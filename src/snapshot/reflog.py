"""Reflog: an append-only log of every commit HEAD has pointed at.

Real Git keeps a reflog per ref (.git/logs/HEAD, plus one per branch).
Snapshot implements only the HEAD reflog -- the one `git reflog`
defaults to showing (`git reflog` is shorthand for `git reflog show
HEAD`), and the one that answers "what did I just do, and how do I
get back." Per-branch reflogs are a real Git feature Snapshot
intentionally omits; the Learn panel explains this simplification
where the reflog is introduced.

STORED FORMAT -- plain text, one line per entry, oldest first (natural
append order). `snapshot reflog` displays entries newest-first, which
is git's own convention, but that's purely a display concern; this
module always returns them in on-disk (oldest-first) order:

    <old_oid> <new_oid> <timestamp>\\t<message>

`old_oid` is 40 zeros for the very first entry ever recorded --
nothing to move FROM yet -- the same sentinel real Git uses.
"""

import time
from dataclasses import dataclass
from pathlib import Path

ZERO_OID = "0" * 40
_REFLOG_RELATIVE_PATH = ("logs", "HEAD")


@dataclass
class ReflogEntry:
    """One recorded HEAD movement."""

    old_oid: str  # ZERO_OID if there was nothing to move from
    new_oid: str
    timestamp: int
    message: str


def _reflog_path(snapshot_dir: Path) -> Path:
    return snapshot_dir.joinpath(*_REFLOG_RELATIVE_PATH)


def append_entry(
    snapshot_dir: Path,
    old_oid: str | None,
    new_oid: str,
    message: str,
    timestamp: int | None = None,
) -> None:
    """Append one entry recording that HEAD moved from old_oid to new_oid.

    old_oid=None is recorded as the zero OID, matching real Git's
    convention for "there was nothing to move from yet" (e.g. the
    very first commit in a repository).
    """
    if timestamp is None:
        timestamp = int(time.time())
    path = _reflog_path(snapshot_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{old_oid or ZERO_OID} {new_oid} {timestamp}\t{message}\n"
    with path.open("a") as f:
        f.write(line)


def read_entries(snapshot_dir: Path) -> list[ReflogEntry]:
    """Return every recorded entry, oldest first (on-disk append order).

    Empty (not missing-file-is-an-error) if nothing has been recorded
    yet -- matching the index/log's own "no file yet means empty"
    convention used throughout this engine.
    """
    path = _reflog_path(snapshot_dir)
    if not path.exists():
        return []

    entries = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        header, _, message = line.partition("\t")
        old_oid, new_oid, timestamp_str = header.split(" ", 2)
        entries.append(ReflogEntry(old_oid=old_oid, new_oid=new_oid, timestamp=int(timestamp_str), message=message))
    return entries
