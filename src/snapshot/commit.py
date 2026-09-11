"""Commit objects: snapshots of the project's history.

A commit does not store file contents directly -- it points at a root
tree (built by Build #2's write_tree_from_index) and, except for the
very first commit, at a parent commit. History is not stored anywhere
separately: it's reconstructed by following parent links backward from
whatever commit a branch ref currently points to.

Like blobs and trees, a commit is stored through the existing generic
object layer unchanged:

    objects.write_object(objects_dir, "commit", payload)

STORED FORMAT (the payload, before objects.py's "commit <size>\\0"
header is added) -- plain text, matching Git closely:

    tree <tree_oid>
    parent <parent_oid>          # omitted entirely for the first commit
    parent <merge_parent_oid>    # present ONLY for merge commits (Build #5)
    author <name> <email> <timestamp> <tz>
    committer <name> <email> <timestamp> <tz>

    <message>

This is byte-compatible with Git: real `git cat-file` and
`git fsck --strict` accept Snapshot's commit objects (see
tests/test_git_compatibility.py).

Simplification: real Git reads author/committer identity from user
configuration (git config user.name / user.email) and records the
local timezone offset. Snapshot hardcodes a single static identity and
always writes UTC ("+0000").

Build #5 note on `merge_parent`: a merge commit is an ORDINARY commit
whose only difference is a second parent line. Rather than generalize
`parent` into a list (which would ripple into every existing caller --
`cmd_log`, `cmd_commit`, every earlier test -- for a capability only
merge commits need), Snapshot adds one new, optional field. This keeps
Build #1-4 code and tests completely unchanged, and it makes "a merge
commit is a normal commit plus one extra field" literally true in the
data model, not just true in prose.
"""

import time
from dataclasses import dataclass
from pathlib import Path

from . import objects

AUTHOR_NAME = "Snapshot User"
AUTHOR_EMAIL = "snapshot@example.com"
TIMEZONE = "+0000"


@dataclass
class Commit:
    """A parsed commit: what it points at, who made it, and why."""

    tree: str                    # 40-char hex OID of the root tree
    parent: str | None           # 40-char hex OID of the (first) parent, or None for the first commit
    author: str                  # "<name> <email> <timestamp> <tz>"
    committer: str               # same shape as author; always identical to it in Snapshot
    message: str
    merge_parent: str | None = None  # second parent; set ONLY on merge commits (Build #5)


def _format_identity(timestamp: int) -> str:
    """Format Snapshot's static identity + a timestamp the way Git formats one: 'Name <email> timestamp tz'."""
    return f"{AUTHOR_NAME} <{AUTHOR_EMAIL}> {timestamp} {TIMEZONE}"


def build_commit(
    tree_oid: str,
    parent_oid: str | None,
    message: str,
    timestamp: int | None = None,
    merge_parent_oid: str | None = None,
) -> Commit:
    """Construct a new Commit with Snapshot's static author/committer identity.

    `timestamp` defaults to the current time; accepting it explicitly
    keeps this function deterministic and easy to test.

    `merge_parent_oid` should only be passed when constructing a merge
    commit; every ordinary commit leaves it as None.
    """
    if timestamp is None:
        timestamp = int(time.time())
    identity = _format_identity(timestamp)
    return Commit(
        tree=tree_oid,
        parent=parent_oid,
        author=identity,
        committer=identity,
        message=message,
        merge_parent=merge_parent_oid,
    )


def encode_commit(commit: Commit) -> bytes:
    """Encode a Commit into Git's commit object payload bytes."""
    lines = [f"tree {commit.tree}"]
    if commit.parent is not None:
        lines.append(f"parent {commit.parent}")
    if commit.merge_parent is not None:
        lines.append(f"parent {commit.merge_parent}")
    lines.append(f"author {commit.author}")
    lines.append(f"committer {commit.committer}")
    header = "\n".join(lines)
    return f"{header}\n\n{commit.message}".encode()


def decode_commit(payload: bytes) -> Commit:
    """Decode a commit object's payload bytes back into a Commit.

    A commit may contain zero, one, or two "parent" header lines (zero
    for the first commit ever made, one for an ordinary commit, two for
    a merge commit). More than two would mean an octopus merge, which
    Snapshot doesn't support.

    Raises:
        ValueError: the payload is malformed -- missing the blank line
            separating headers from the message, missing a required
            header, containing an unrecognized header line, or
            containing more than two parent lines.
    """
    text = payload.decode()
    if "\n\n" not in text:
        raise ValueError("malformed commit: missing blank line between header and message")

    header_text, message = text.split("\n\n", 1)

    tree_oid = None
    parent_oids: list[str] = []
    author = None
    committer = None

    for line in header_text.split("\n"):
        if not line:
            continue
        key, sep, value = line.partition(" ")
        if not sep:
            raise ValueError(f"malformed commit: unrecognized header line {line!r}")
        if key == "tree":
            tree_oid = value
        elif key == "parent":
            parent_oids.append(value)
        elif key == "author":
            author = value
        elif key == "committer":
            committer = value
        else:
            raise ValueError(f"malformed commit: unrecognized header line {line!r}")

    if tree_oid is None:
        raise ValueError("malformed commit: missing required 'tree' header")
    if author is None:
        raise ValueError("malformed commit: missing required 'author' header")
    if committer is None:
        raise ValueError("malformed commit: missing required 'committer' header")
    if len(parent_oids) > 2:
        raise ValueError(
            "malformed commit: more than two parent lines (octopus merges are not supported)"
        )

    parent = parent_oids[0] if len(parent_oids) >= 1 else None
    merge_parent = parent_oids[1] if len(parent_oids) >= 2 else None

    return Commit(
        tree=tree_oid, parent=parent, author=author, committer=committer,
        message=message, merge_parent=merge_parent,
    )


def store_commit(objects_dir: Path, commit: Commit) -> str:
    """Encode and store a commit object through the generic object layer. Returns its OID."""
    payload = encode_commit(commit)
    return objects.write_object(objects_dir, "commit", payload)


def read_commit(objects_dir: Path, oid: str) -> Commit:
    """Read and decode a commit object by OID.

    Raises:
        FileNotFoundError: no object exists for this OID.
        ValueError: the object exists but isn't a commit, or its
            payload is malformed.
    """
    obj_type, payload = objects.read_object(objects_dir, oid)
    if obj_type != "commit":
        raise ValueError(f"object {oid} is a {obj_type}, not a commit")
    return decode_commit(payload)