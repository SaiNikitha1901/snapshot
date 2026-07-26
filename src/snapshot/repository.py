"""Repository initialization.

For Build Point #1 this only creates the object database directory.
Later build points will add the index file, refs/, and HEAD here --
this module is the natural home for those as they're introduced.
"""

from pathlib import Path

SNAPSHOT_DIR_NAME = ".snapshot"


def init_repository(path: Path) -> Path:
    """Create a new Snapshot repository rooted at `path`.

    Returns the path to the created .snapshot directory.
    """
    snapshot_dir = path / SNAPSHOT_DIR_NAME
    objects_dir = snapshot_dir / "objects"
    objects_dir.mkdir(parents=True, exist_ok=True)
    return snapshot_dir