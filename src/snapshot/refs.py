"""References: HEAD and branch refs.

Real Git supports many kinds of refs (branches, tags, remote-tracking
branches, etc.) and a general ref-resolution algorithm. Snapshot only
supports lightweight branches under refs/heads/, reached through HEAD.
This module is intentionally small and only implements what that
requires.

HEAD can be in one of two states:

  SYMBOLIC (normal): a text file pointing at a branch ref by name:
      ref: refs/heads/main

  DETACHED: a text file containing a commit OID directly:
      3b18e512dba79e4c8300dd08aeb37f8e728b8dad

A branch ref (e.g. .snapshot/refs/heads/main) is a plain text file
containing a single commit OID as 40 hex characters. A branch ref
that doesn't exist yet means that branch has no commits. Branches are
intentionally lightweight: creating one only ever writes this one
small file -- it never touches objects, the working directory, or the
index.
"""

from pathlib import Path

HEAD_PREFIX = "ref: "
OID_LENGTH = 40
_HEX_DIGITS = set("0123456789abcdef")


def looks_like_oid(value: str) -> bool:
    """Return True if value is shaped like a 40-character hex SHA-1 OID.

    This is a format check only -- it does not confirm an object with
    that OID actually exists.
    """
    return len(value) == OID_LENGTH and all(c in _HEX_DIGITS for c in value)


def read_head(snapshot_dir: Path) -> str:
    """Read HEAD's raw contents -- either "ref: refs/heads/main" or a bare commit OID."""
    return (snapshot_dir / "HEAD").read_text().strip()


def is_detached(snapshot_dir: Path) -> bool:
    """Return True if HEAD holds a commit OID directly rather than pointing at a branch."""
    return not read_head(snapshot_dir).startswith(HEAD_PREFIX)


def current_branch_ref_path(snapshot_dir: Path) -> Path:
    """Resolve HEAD's symbolic reference to a branch ref file's path.

    Only meaningful when HEAD is symbolic. Does not require the branch
    ref file to exist yet (a branch with no commits has no ref file).

    Raises:
        ValueError: HEAD is missing, detached, or not a well-formed
            symbolic reference.
    """
    head_path = snapshot_dir / "HEAD"
    if not head_path.exists():
        raise ValueError("HEAD not found -- is this a Snapshot repository?")

    head_content = read_head(snapshot_dir)
    if not head_content.startswith(HEAD_PREFIX):
        if looks_like_oid(head_content):
            raise ValueError("HEAD is detached (points directly at a commit), not a branch")
        raise ValueError(f"malformed HEAD: {head_content!r}")

    ref_relative_path = head_content[len(HEAD_PREFIX):].strip()
    if not ref_relative_path:
        raise ValueError("malformed HEAD: 'ref: ' with no path")

    return snapshot_dir / ref_relative_path


def current_branch_name(snapshot_dir: Path) -> str:
    """Return the current branch's name (e.g. "main"), read from HEAD.

    Raises:
        ValueError: HEAD is detached or malformed.
    """
    return current_branch_ref_path(snapshot_dir).name


def read_branch_oid(ref_path: Path) -> str | None:
    """Read the commit OID a branch ref currently points to.

    Returns None if the ref file doesn't exist -- the branch has no
    commits yet.
    """
    if not ref_path.exists():
        return None
    return ref_path.read_text().strip()


def resolve_head(snapshot_dir: Path) -> str | None:
    """Resolve HEAD all the way to a commit OID.

    Returns None only when HEAD is symbolic and its branch has no
    commits yet. A detached HEAD always resolves to a concrete OID,
    since you can only detach onto a commit that already exists.

    Raises:
        ValueError: HEAD is missing or malformed (neither a valid
            symbolic reference nor a valid-looking commit OID).
    """
    head_content = read_head(snapshot_dir)

    if head_content.startswith(HEAD_PREFIX):
        ref_relative_path = head_content[len(HEAD_PREFIX):].strip()
        if not ref_relative_path:
            raise ValueError("malformed HEAD: 'ref: ' with no path")
        return read_branch_oid(snapshot_dir / ref_relative_path)

    if looks_like_oid(head_content):
        return head_content

    raise ValueError(f"malformed HEAD: {head_content!r}")


def update_branch_ref(ref_path: Path, commit_oid: str) -> None:
    """Point a branch ref at a new commit OID.

    Creates the ref file (and any missing parent directories) if this
    is the branch's first commit.
    """
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(commit_oid + "\n")


def update_head(snapshot_dir: Path, commit_oid: str, *, reflog_message: str | None = None) -> None:
    """Advance HEAD to point at a new commit, after a successful commit.

    If HEAD is symbolic (on a branch), this updates that branch's ref
    file; HEAD itself, and every other branch, is left untouched. If
    HEAD is detached, this overwrites HEAD directly with the new OID
    -- no branch moves. This is the one place "which thing moves when
    you commit" is decided -- and, since every HEAD-moving operation
    (commit, merge) ends up calling this, the one place a reflog entry
    is recorded for all of them. `reflog_message` is optional so
    existing callers that only care about pointer mechanics (chiefly
    tests) are unaffected; real callers pass a real message.
    """
    old_oid = resolve_head(snapshot_dir)
    if is_detached(snapshot_dir):
        (snapshot_dir / "HEAD").write_text(commit_oid + "\n")
    else:
        branch_ref_path = current_branch_ref_path(snapshot_dir)
        update_branch_ref(branch_ref_path, commit_oid)
    _record_reflog(snapshot_dir, old_oid, commit_oid, reflog_message)


def set_symbolic_head(snapshot_dir: Path, branch_name: str, *, reflog_message: str | None = None) -> None:
    """Point HEAD at a branch by name (used by `checkout <branch>`)."""
    old_oid = resolve_head(snapshot_dir)
    (snapshot_dir / "HEAD").write_text(f"{HEAD_PREFIX}refs/heads/{branch_name}\n")
    new_oid = read_branch_oid(snapshot_dir / "refs" / "heads" / branch_name)
    if new_oid is not None:
        _record_reflog(snapshot_dir, old_oid, new_oid, reflog_message)


def set_detached_head(snapshot_dir: Path, commit_oid: str, *, reflog_message: str | None = None) -> None:
    """Point HEAD directly at a commit OID (used by `checkout <commit_oid>`)."""
    old_oid = resolve_head(snapshot_dir)
    (snapshot_dir / "HEAD").write_text(commit_oid + "\n")
    _record_reflog(snapshot_dir, old_oid, commit_oid, reflog_message)


def _record_reflog(snapshot_dir: Path, old_oid: str | None, new_oid: str, message: str | None) -> None:
    from . import reflog as reflog_mod  # local import: reflog.py never needs to import refs.py, this keeps it that way

    reflog_mod.append_entry(snapshot_dir, old_oid, new_oid, message or f"updated HEAD to {new_oid[:7]}")


def list_branches(snapshot_dir: Path) -> list[str]:
    """Return all branch names under refs/heads/, sorted alphabetically."""
    heads_dir = snapshot_dir / "refs" / "heads"
    if not heads_dir.exists():
        return []
    return sorted(p.name for p in heads_dir.iterdir() if p.is_file())


def branch_exists(snapshot_dir: Path, branch_name: str) -> bool:
    """Return True if a branch ref file exists for branch_name."""
    return (snapshot_dir / "refs" / "heads" / branch_name).is_file()


def create_branch(snapshot_dir: Path, branch_name: str) -> str:
    """Create a new branch pointing at HEAD's current commit.

    This is a lightweight, pointer-only operation: it creates exactly
    one small ref file and touches nothing else -- no objects, no
    working directory changes, no index changes. It does NOT switch
    HEAD to the new branch; creating a branch and checking it out are
    deliberately separate operations.

    Returns the commit OID the new branch now points to.

    Raises:
        ValueError: branch_name is invalid, the branch already
            exists, or HEAD has no commits yet to branch from.
    """
    if not branch_name or "/" in branch_name or branch_name in {".", ".."}:
        raise ValueError(f"'{branch_name}' is not a valid branch name")

    if branch_exists(snapshot_dir, branch_name):
        raise ValueError(f"branch '{branch_name}' already exists")

    commit_oid = resolve_head(snapshot_dir)
    if commit_oid is None:
        raise ValueError("cannot create a branch: no commits yet")

    branch_ref_path = snapshot_dir / "refs" / "heads" / branch_name
    update_branch_ref(branch_ref_path, commit_oid)
    return commit_oid