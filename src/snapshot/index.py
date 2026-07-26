"""The index (staging area): a snapshot-in-progress of what the next commit will contain.

Each index entry associates a repository-relative path with the mode and
blob OID of the file staged at that path. The index does NOT store file
contents -- those already live in blob objects under .snapshot/objects/.
Conceptually:

    src/main.py -> mode 100644 -> Blob abc123...

Simplification: real Git's index is a binary file (see gitformat-index(5))
that also stores filesystem metadata -- mtime, size, inode, uid/gid, stat
cache flags -- used to speed up detecting changed files without rehashing
everything. Snapshot's index is a small, deterministic plain-text file:
one line per entry, "<mode> <oid> <path>", sorted by path. It intentionally
omits the filesystem-metadata cache; every `snapshot add` re-reads and
re-hashes the file's actual bytes. This is simpler to read and reason
about, at the cost of the performance optimization real Git's cache
provides.

The index file is created lazily: `snapshot init` does not create it. An
index file that doesn't exist yet and an index with zero entries mean
exactly the same thing (nothing staged), so there's no separate "create
an empty index" step.
"""

import stat as stat_module
from dataclasses import dataclass
from pathlib import Path

from . import blob


@dataclass
class IndexEntry:
    """A single staged file: where it lives, its mode, and its blob OID."""

    path: str   # repository-relative, forward-slash separated
    mode: str   # "100644" (regular file) or "100755" (executable)
    oid: str    # 40-character hex OID of the staged blob


IGNORED_DIR_NAMES = {".snapshot", ".git", ".venv", "__pycache__", ".pytest_cache"}


def file_mode(path: Path) -> str:
    """Determine a file's Git-style mode.

    Simplification: real Git also has modes for symlinks (120000) and
    submodule gitlinks (160000). Snapshot only distinguishes regular
    files (100644) from executable files (100755).
    """
    st = path.stat()
    if st.st_mode & stat_module.S_IXUSR:
        return "100755"
    return "100644"


def read_index(index_path: Path) -> list[IndexEntry]:
    """Read all staged entries, sorted by path. Empty if no index file exists yet."""
    if not index_path.exists():
        return []

    entries = []
    for line in index_path.read_text().splitlines():
        if not line.strip():
            continue
        mode, oid, path = line.split(" ", 2)
        entries.append(IndexEntry(path=path, mode=mode, oid=oid))
    return sorted(entries, key=lambda e: e.path)


def write_index(index_path: Path, entries: list[IndexEntry]) -> None:
    """Write the index as one sorted, deterministic line per entry.

    Format: "<mode> <oid> <path>" -- e.g.
        100644 3b18e512dba79e4c8300dd08aeb37f8e728b8dad README.md

    This is a Snapshot-specific plain-text format, not a reproduction of
    Git's binary index (see module docstring).
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_entries = sorted(entries, key=lambda e: e.path)
    lines = [f"{e.mode} {e.oid} {e.path}" for e in sorted_entries]
    index_path.write_text("\n".join(lines) + ("\n" if lines else ""))


def stage_entry(index_path: Path, entry: IndexEntry) -> None:
    """Add or update a single entry in the index by path.

    If `entry.path` is already staged, its old entry is replaced;
    otherwise the new entry is added.
    """
    entries = [e for e in read_index(index_path) if e.path != entry.path]
    entries.append(entry)
    write_index(index_path, entries)


def stage_file(objects_dir: Path, index_path: Path, repo_root: Path, file_path: Path) -> IndexEntry:
    """Stage a single file end-to-end: store its blob, then record it in the index.

    This is the one place staging logic lives -- both the `snapshot add`
    CLI command and any future caller (e.g. `snapshot commit` staging
    logic, if that's ever added) should call this rather than duplicating
    these steps.

    Returns the resulting IndexEntry.

    Raises:
        ValueError: file_path is not inside repo_root.
    """
    oid = blob.store_blob(objects_dir, file_path)

    try:
        rel_path = file_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"'{file_path}' is outside the repository") from exc

    mode = file_mode(file_path)
    entry = IndexEntry(path=rel_path, mode=mode, oid=oid)
    stage_entry(index_path, entry)
    return entry


def collect_stageable_files(root: Path) -> list[Path]:
    """Recursively collect regular files under root for `snapshot add .`.

    This is NOT a .gitignore implementation -- it just skips Snapshot's
    own directory plus a few common development/tooling directories so
    manual experiments don't accidentally stage them.
    """
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIR_NAMES for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return files