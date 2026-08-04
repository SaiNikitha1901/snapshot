"""References: HEAD and branch refs.

Real Git supports many kinds of refs (branches, tags, remote-tracking
branches, etc.) and a general ref-resolution algorithm. Snapshot only
supports a single branch, "main", reached through HEAD. This module is
intentionally small and only implements what that requires.

HEAD is a SYMBOLIC reference: a plain text file that points at a
branch ref rather than storing a commit OID directly:

    ref: refs/heads/main

A branch ref (e.g. .snapshot/refs/heads/main) is a plain text file
containing a single commit OID as 40 hex characters. A branch ref
that doesn't exist yet means that branch has no commits.
"""

from pathlib import Path

HEAD_PREFIX = "ref: "


def read_head(snapshot_dir: Path) -> str:
    """Read HEAD's raw contents, e.g. "ref: refs/heads/main"."""
    return (snapshot_dir / "HEAD").read_text().strip()


def current_branch_ref_path(snapshot_dir: Path) -> Path:
    """Resolve HEAD's symbolic reference to a branch ref file's path.

    This only resolves the *path* -- it does not require that path to
    exist yet (a branch with no commits has no ref file).

    Raises:
        ValueError: HEAD is missing or not a well-formed symbolic
            reference ("ref: <path>").
    """
    head_path = snapshot_dir / "HEAD"
    if not head_path.exists():
        raise ValueError("HEAD not found -- is this a Snapshot repository?")

    head_content = read_head(snapshot_dir)
    if not head_content.startswith(HEAD_PREFIX):
        raise ValueError(f"malformed HEAD: expected 'ref: <path>', got {head_content!r}")

    ref_relative_path = head_content[len(HEAD_PREFIX):].strip()
    if not ref_relative_path:
        raise ValueError("malformed HEAD: 'ref: ' with no path")

    return snapshot_dir / ref_relative_path


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

    Returns None if HEAD's branch exists but has no commits yet.

    Raises:
        ValueError: HEAD is missing or malformed.
    """
    ref_path = current_branch_ref_path(snapshot_dir)
    return read_branch_oid(ref_path)


def update_branch_ref(ref_path: Path, commit_oid: str) -> None:
    """Point a branch ref at a new commit OID.

    Creates the ref file (and any missing parent directories) if this
    is the branch's first commit.
    """
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(commit_oid + "\n")