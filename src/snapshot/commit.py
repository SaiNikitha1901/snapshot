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
    author <name> <email> <timestamp>
    committer <name> <email> <timestamp>

    <message>

Simplification: real Git also writes a timezone offset after the
timestamp (e.g. "+0000") and reads author/committer identity from user
configuration (git config user.name / user.email). Snapshot hardcodes
a single static identity and omits the timezone.
"""

import time
from dataclasses import dataclass
from pathlib import Path

from . import objects

AUTHOR_NAME = "Snapshot User"
AUTHOR_EMAIL = "snapshot@example.com"


@dataclass
class Commit:
    """A parsed commit: what it points at, who made it, and why."""

    tree: str               # 40-char hex OID of the root tree
    parent: str | None      # 40-char hex OID of the parent commit, or None for the first commit
    author: str             # "<name> <email> <timestamp>"
    committer: str          # same shape as author; always identical to it in Snapshot
    message: str


def _format_identity(timestamp: int) -> str:
    """Format Snapshot's static identity + a timestamp the way Git formats one: 'Name <email> timestamp'."""
    return f"{AUTHOR_NAME} <{AUTHOR_EMAIL}> {timestamp}"


def build_commit(
    tree_oid: str, parent_oid: str | None, message: str, timestamp: int | None = None
) -> Commit:
    """Construct a new Commit with Snapshot's static author/committer identity.

    `timestamp` defaults to the current time; accepting it explicitly
    keeps this function deterministic and easy to test.
    """
    if timestamp is None:
        timestamp = int(time.time())
    identity = _format_identity(timestamp)
    return Commit(tree=tree_oid, parent=parent_oid, author=identity, committer=identity, message=message)


def encode_commit(commit: Commit) -> bytes:
    """Encode a Commit into Git's commit object payload bytes."""
    lines = [f"tree {commit.tree}"]
    if commit.parent is not None:
        lines.append(f"parent {commit.parent}")
    lines.append(f"author {commit.author}")
    lines.append(f"committer {commit.committer}")
    header = "\n".join(lines)
    return f"{header}\n\n{commit.message}".encode()


def decode_commit(payload: bytes) -> Commit:
    """Decode a commit object's payload bytes back into a Commit.

    Raises:
        ValueError: the payload is malformed -- missing the blank line
            separating headers from the message, missing a required
            header, or containing an unrecognized header line.
    """
    text = payload.decode()
    if "\n\n" not in text:
        raise ValueError("malformed commit: missing blank line between header and message")

    header_text, message = text.split("\n\n", 1)

    tree_oid = None
    parent_oid = None
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
            parent_oid = value
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

    return Commit(tree=tree_oid, parent=parent_oid, author=author, committer=committer, message=message)


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