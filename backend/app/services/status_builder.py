"""Builds the read-only Repository Status DTO: HEAD, current branch,
current commit, working directory, and index state.

Snapshot's index has no first-class "unmerged" entries (real Git's
index has stage 1/2/3 slots for conflicts; this engine doesn't
implement that -- see merge.py's module docstring). Conflicts are
detected here by scanning tracked/untracked files for Git-style
conflict markers, which is exactly what merge.py writes into the
working directory on a conflicted merge. This keeps status accurate
on a fresh GET (e.g. page load) without needing to remember the last
command's result.
"""

from pathlib import Path

from snapshot import blob as blob_mod
from snapshot import commit as commit_mod
from snapshot import index as index_mod
from snapshot import refs as refs_mod
from snapshot import tree as tree_mod

from app.schemas.status import RepositoryStatus

_CONFLICT_MARKERS = (b"<<<<<<< ", b"=======\n", b">>>>>>> ")


def build_status(snapshot_dir: Path, objects_dir: Path, index_path: Path, repo_root: Path) -> RepositoryStatus:
    if not (objects_dir).exists():
        return RepositoryStatus(
            initialized=False,
            head_detached=False,
            current_branch=None,
            current_commit_oid=None,
            working_directory_clean=True,
            staged_paths=[],
            unstaged_paths=[],
            untracked_paths=[],
            conflicted_paths=[],
        )

    head_detached = refs_mod.is_detached(snapshot_dir)
    current_branch = None if head_detached else refs_mod.current_branch_name(snapshot_dir)
    current_commit_oid = refs_mod.resolve_head(snapshot_dir)

    index_entries = index_mod.read_index(index_path)
    index_map = {e.path: e.oid for e in index_entries}

    tree_map: dict[str, str] = {}
    if current_commit_oid is not None:
        commit_obj = commit_mod.read_commit(objects_dir, current_commit_oid)
        tree_map = {e.path: e.oid for e in tree_mod.flatten_tree_to_entries(objects_dir, commit_obj.tree)}

    staged_paths = sorted(path for path, oid in index_map.items() if tree_map.get(path) != oid)

    unstaged_paths = []
    for entry in index_entries:
        file_path = repo_root / entry.path
        if not file_path.is_file():
            unstaged_paths.append(entry.path)
        elif blob_mod.compute_blob_oid(file_path) != entry.oid:
            unstaged_paths.append(entry.path)
    unstaged_paths.sort()

    all_files = index_mod.collect_stageable_files(repo_root)
    untracked_paths = sorted(
        p.resolve().relative_to(repo_root.resolve()).as_posix()
        for p in all_files
        if p.resolve().relative_to(repo_root.resolve()).as_posix() not in index_map
    )

    conflicted_paths = sorted(
        p.resolve().relative_to(repo_root.resolve()).as_posix()
        for p in all_files
        if _has_conflict_markers(p)
    )

    working_directory_clean = not (unstaged_paths or untracked_paths or conflicted_paths)

    return RepositoryStatus(
        initialized=True,
        head_detached=head_detached,
        current_branch=current_branch,
        current_commit_oid=current_commit_oid,
        working_directory_clean=working_directory_clean,
        staged_paths=staged_paths,
        unstaged_paths=unstaged_paths,
        untracked_paths=untracked_paths,
        conflicted_paths=conflicted_paths,
    )


def _has_conflict_markers(file_path: Path) -> bool:
    try:
        content = file_path.read_bytes()
    except OSError:
        return False
    return all(marker in content for marker in _CONFLICT_MARKERS)
