"""Repository initialization.

Creates the minimum on-disk layout Snapshot needs, growing lazily as
new capabilities are added:
  - Build #1: .snapshot/objects/
  - Build #2: .snapshot/index          (created lazily by the first `add`)
  - Build #3: .snapshot/HEAD, .snapshot/refs/heads/
"""

from pathlib import Path

SNAPSHOT_DIR_NAME = ".snapshot"
DEFAULT_HEAD_CONTENT = "ref: refs/heads/main\n"


def init_repository(path: Path) -> Path:
    """Create a new Snapshot repository rooted at `path`.

    Creates:
      - .snapshot/objects/     content-addressable object store
      - .snapshot/refs/heads/  empty directory scaffold for branch refs
      - .snapshot/HEAD         symbolic reference to refs/heads/main

    Does NOT create .snapshot/refs/heads/main itself, and does NOT
    create .snapshot/index. Both are created lazily -- the index by
    the first `snapshot add`, and refs/heads/main by the first
    successful `snapshot commit`. A branch ref that doesn't exist yet
    means "this branch has no commits", the same way a missing index
    file means "nothing is staged".

    This matches real Git: a freshly initialized repository has an
    empty refs/heads/ directory and a HEAD that already points at
    "refs/heads/main", even though main doesn't exist as a branch
    with any commits yet.

    Safe to call on an already-initialized repository: existing files
    are left untouched.
    """
    snapshot_dir = path / SNAPSHOT_DIR_NAME

    objects_dir = snapshot_dir / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)

    refs_heads_dir = snapshot_dir / "refs" / "heads"
    refs_heads_dir.mkdir(parents=True, exist_ok=True)

    head_path = snapshot_dir / "HEAD"
    if not head_path.exists():
        head_path.write_text(DEFAULT_HEAD_CONTENT)

    return snapshot_dir