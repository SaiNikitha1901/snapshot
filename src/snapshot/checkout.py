"""Checkout: switching what HEAD follows, and restoring the working
directory and index to match.

Checkout NEVER creates objects -- it only reads blobs, trees, and
commits that already exist, and reproduces their content on disk and
in the index. The commit graph itself is completely unaffected by a
checkout; only three things change on a successful one:

  1. The working directory's file contents (and which files exist)
  2. The index (overwritten to exactly match the checked-out commit)
  3. HEAD (repointed at a branch, or directly at a commit if detached)

Before doing any of that, checkout refuses if it would silently
discard uncommitted work -- see unstaged_changes_exist and
staged_changes_exist below.
"""

import stat
from pathlib import Path

from . import blob, commit, index, objects, refs, tree


def unstaged_changes_exist(repo_root: Path, index_path: Path) -> bool:
    """True if any tracked file's on-disk content no longer matches what's staged.

    This is "changes not staged for commit" in Git's terms: for every
    entry already in the index, recompute the blob OID the file's
    *current* bytes on disk would hash to, and compare it against the
    OID recorded in the index. A tracked file that was deleted also
    counts as an unstaged change.

    Simplification: untracked files (present on disk but never
    staged) are not detected here -- matching Git's behavior that only
    tracked files can block a checkout on their own.
    """
    for entry in index.read_index(index_path):
        file_path = repo_root / entry.path
        if not file_path.is_file():
            return True
        if blob.compute_blob_oid(file_path) != entry.oid:
            return True
    return False


def staged_changes_exist(objects_dir: Path, index_path: Path, commit_oid: str | None) -> bool:
    """True if the index no longer matches the current commit's tree.

    This is "changes to be committed" in Git's terms.
    """
    entries = index.read_index(index_path)

    if commit_oid is None:
        return bool(entries)

    commit_obj = commit.read_commit(objects_dir, commit_oid)
    tree_entries = tree.flatten_tree_to_entries(objects_dir, commit_obj.tree)

    index_map = {e.path: e.oid for e in entries}
    tree_map = {e.path: e.oid for e in tree_entries}
    return index_map != tree_map


def _ensure_safe_to_checkout(
    objects_dir: Path, index_path: Path, repo_root: Path, current_commit_oid: str | None
) -> None:
    """Raise ValueError if checking out now would silently discard local work."""
    if unstaged_changes_exist(repo_root, index_path):
        raise ValueError(
            "checkout would overwrite uncommitted changes in your working "
            "directory; commit or discard them first"
        )
    if staged_changes_exist(objects_dir, index_path, current_commit_oid):
        raise ValueError(
            "checkout would overwrite staged changes that haven't been "
            "committed; commit or unstage them first"
        )


def restore_to_commit(objects_dir: Path, index_path: Path, repo_root: Path, commit_oid: str) -> None:
    """Overwrite the working directory and index to match commit_oid's tree.

    Only reads existing objects -- never creates new ones. Files that
    were tracked before but aren't part of the target tree are
    removed; every file the target tree specifies is written (or
    overwritten). The index is then rewritten to exactly mirror the
    target tree, so working directory == index == checked-out commit.

    Simplification: directories left empty after their last tracked
    file is removed are not cleaned up. They're a harmless leftover,
    not a correctness issue -- Snapshot doesn't track directories as
    first-class entities, only tree objects do.

    Public (Build #5): merge.py reuses this exact function for the
    final "sync working directory + index to the result" step after a
    successful fast-forward or three-way merge, instead of
    reimplementing restoration logic.
    """
    commit_obj = commit.read_commit(objects_dir, commit_oid)
    target_entries = tree.flatten_tree_to_entries(objects_dir, commit_obj.tree)

    old_paths = {e.path for e in index.read_index(index_path)}
    new_paths = {e.path for e in target_entries}

    for stale_path in old_paths - new_paths:
        stale_file = repo_root / stale_path
        if stale_file.exists():
            stale_file.unlink()

    for entry in target_entries:
        file_path = repo_root / entry.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        _, content = objects.read_object(objects_dir, entry.oid)
        file_path.write_bytes(content)
        if entry.mode == "100755":
            file_path.chmod(file_path.stat().st_mode | stat.S_IXUSR)

    index.write_index(index_path, target_entries)


def checkout_branch(
    snapshot_dir: Path, objects_dir: Path, index_path: Path, repo_root: Path, branch_name: str
) -> str:
    """Switch to an existing branch.

    Safety-checks for local work, restores the working directory and
    index from the branch's tip commit, then points HEAD at the
    branch (a symbolic reference, not a raw OID).

    Returns the commit OID now checked out.

    Raises:
        ValueError: the branch doesn't exist, or local changes would
            be lost.
    """
    if not refs.branch_exists(snapshot_dir, branch_name):
        raise ValueError(f"branch '{branch_name}' does not exist")

    current_commit_oid = refs.resolve_head(snapshot_dir)
    _ensure_safe_to_checkout(objects_dir, index_path, repo_root, current_commit_oid)
    from_label = _checkout_from_label(snapshot_dir, current_commit_oid)

    target_commit_oid = refs.read_branch_oid(snapshot_dir / "refs" / "heads" / branch_name)
    restore_to_commit(objects_dir, index_path, repo_root, target_commit_oid)
    refs.set_symbolic_head(
        snapshot_dir, branch_name, reflog_message=f"checkout: moving from {from_label} to {branch_name}"
    )

    return target_commit_oid


def _checkout_from_label(snapshot_dir: Path, current_commit_oid: str | None) -> str:
    """A short, human-readable label for "where HEAD was" before a
    checkout, for the reflog message -- a branch name if HEAD was
    symbolic, a short commit OID if detached."""
    if refs.is_detached(snapshot_dir):
        return current_commit_oid[:7] if current_commit_oid else "unborn"
    try:
        return refs.current_branch_name(snapshot_dir)
    except ValueError:
        return "unborn"


def checkout_commit(
    snapshot_dir: Path, objects_dir: Path, index_path: Path, repo_root: Path, commit_oid: str
) -> str:
    """Detach HEAD onto a specific commit.

    Safety-checks for local work, restores the working directory and
    index from that commit, then points HEAD directly at the commit's
    OID -- not at any branch. Subsequent commits will advance HEAD
    alone; no branch will move.

    Returns the commit OID now checked out.

    Raises:
        ValueError: commit_oid isn't a known branch or a valid commit
            OID, or local changes would be lost.
    """
    if not refs.looks_like_oid(commit_oid):
        raise ValueError(f"'{commit_oid}' is not a known branch or a valid commit OID")

    try:
        obj_type, _ = objects.read_object(objects_dir, commit_oid)
    except FileNotFoundError:
        raise ValueError(f"'{commit_oid}' is not a known branch or a valid commit OID")
    if obj_type != "commit":
        raise ValueError(f"object '{commit_oid}' is a {obj_type}, not a commit")

    current_commit_oid = refs.resolve_head(snapshot_dir)
    _ensure_safe_to_checkout(objects_dir, index_path, repo_root, current_commit_oid)
    from_label = _checkout_from_label(snapshot_dir, current_commit_oid)

    restore_to_commit(objects_dir, index_path, repo_root, commit_oid)
    refs.set_detached_head(
        snapshot_dir, commit_oid, reflog_message=f"checkout: moving from {from_label} to {commit_oid[:7]}"
    )

    return commit_oid