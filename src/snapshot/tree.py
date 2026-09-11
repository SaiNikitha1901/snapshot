"""Tree objects: Git's representation of directory structure.

A tree entry associates a mode and name with the OID of the object it
references -- a blob for a regular file, another tree for a directory.
This module handles tree-entry encoding/decoding and building the tree
hierarchy from staged index entries. It does NOT duplicate hashing,
compression, or storage -- every tree it builds is written through the
existing generic `objects.write_object`, exactly like blobs are.

STORED FORMAT (the actual bytes inside a tree object, after objects.py's
"tree <size>\\0" header is added):

    <mode> <name>\\0<raw 20-byte OID>   (repeated, concatenated; entries sorted by name)

Two details that matter and are easy to get wrong:
  * The OID inside a tree entry is the raw 20 binary bytes, NOT the
    40-character hex string used everywhere else in this codebase.
  * A directory's mode is encoded as "40000" (5 characters, no leading
    zero) -- NOT "040000". This matches real Git's actual on-disk bytes.
    Displaying it zero-padded as "040000" (as `git ls-tree` and our own
    `ls-tree` command do) is a DISPLAY convention, not the stored form.
"""

from dataclasses import dataclass
from pathlib import Path

from . import objects
from .index import IndexEntry


@dataclass
class TreeEntry:
    """A single entry in a tree: this entry's own mode, name, and OID.

    `name` is just this entry's own name (e.g. "utils.py"), never a full
    path -- directory structure is expressed by nesting trees inside
    trees, not by longer names.
    """

    mode: str   # "100644", "100755", or "40000" (tree) -- unpadded, as stored
    name: str
    oid: str    # 40-character hex OID of the referenced blob or tree


def entry_type(mode: str) -> str:
    """Return 'tree' or 'blob' based on an entry's mode."""
    return "tree" if mode == "40000" else "blob"


def encode_tree_entry(entry: TreeEntry) -> bytes:
    """Encode a single tree entry as Git would: "<mode> <name>\\0<raw OID>"."""
    header = f"{entry.mode} {entry.name}".encode()
    raw_oid = bytes.fromhex(entry.oid)
    return header + b"\0" + raw_oid


def encode_tree(entries: list[TreeEntry]) -> bytes:
    """Encode a list of tree entries into a tree object's payload bytes.

    Entries are sorted the way Git sorts them: by name, but comparing
    directory entries as if their name had a trailing "/". This only
    changes ordering when a file and a directory share a name prefix
    (e.g. "lib.txt" sorts before the directory "lib", because "." < "/"),
    but without it Snapshot's tree OIDs would diverge from Git's and
    `git fsck` would reject the tree as unsorted.
    """
    sorted_entries = sorted(entries, key=lambda e: e.name + "/" if e.mode == "40000" else e.name)
    return b"".join(encode_tree_entry(e) for e in sorted_entries)


def decode_tree_payload(payload: bytes) -> list[TreeEntry]:
    """Decode a tree object's payload bytes back into TreeEntry objects.

    Raises:
        ValueError: the payload is malformed (missing separators, or a
            truncated OID at the end of an entry).
    """
    entries = []
    rest = payload

    while rest:
        header, sep, rest = rest.partition(b"\0")
        if sep != b"\0":
            raise ValueError("malformed tree payload: missing header separator")

        mode, sep, name = header.decode().partition(" ")
        if not sep or not mode or not name:
            raise ValueError(f"malformed tree entry header: {header!r}")

        raw_oid, rest = rest[:20], rest[20:]
        if len(raw_oid) != 20:
            raise ValueError("malformed tree payload: truncated object OID")

        entries.append(TreeEntry(mode=mode, name=name, oid=raw_oid.hex()))

    return entries


def _group_entries_by_path(index_entries: list[IndexEntry]) -> dict:
    """Turn a flat list of index entries into a nested dict mirroring
    directory structure, e.g.:

        {"README.md": <entry>, "src": {"utils.py": <entry>, ...}}

    Leaf values are IndexEntry objects; intermediate values are nested
    dicts representing subdirectories.
    """
    root: dict = {}
    for entry in index_entries:
        parts = entry.path.split("/")
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = entry
    return root


def _write_tree_node(objects_dir: Path, node: dict) -> str:
    """Recursively build and store the tree object for one directory level.

    Subdirectories are processed first (bottom-up), since a directory's
    tree entry needs that subtree's OID before it can be encoded.
    """
    entries = []
    for name, value in node.items():
        if isinstance(value, dict):
            subtree_oid = _write_tree_node(objects_dir, value)
            entries.append(TreeEntry(mode="40000", name=name, oid=subtree_oid))
        else:
            entries.append(TreeEntry(mode=value.mode, name=name, oid=value.oid))

    payload = encode_tree(entries)
    return objects.write_object(objects_dir, "tree", payload)


def write_tree_from_index(objects_dir: Path, index_entries: list[IndexEntry]) -> str:
    """Build the full tree hierarchy from staged index entries.

    Groups entries into their directory structure, recursively builds
    and stores each subtree bottom-up, then stores and returns the OID
    of the root tree.

    Raises:
        ValueError: the index is empty -- there is nothing to build a
            tree from. (Real Git allows an empty tree; we treat this as
            deliberately unsupported for now rather than silently
            producing a tree object with zero entries.)
    """
    if not index_entries:
        raise ValueError("cannot write-tree: the index is empty (nothing staged)")

    root_node = _group_entries_by_path(index_entries)
    return _write_tree_node(objects_dir, root_node)


def flatten_tree_to_entries(objects_dir: Path, tree_oid: str, path_prefix: str = "") -> list[IndexEntry]:
    """Recursively walk a tree object and flatten it back into a list of
    (path, mode, oid) entries -- the exact inverse of the grouping step
    inside write_tree_from_index.

    Used by checkout (Build #4) to figure out what the working
    directory and index should look like for a given commit, without
    ever creating new objects -- this function only reads.
    """
    _, payload = objects.read_object(objects_dir, tree_oid)
    entries = decode_tree_payload(payload)

    flattened: list[IndexEntry] = []
    for entry in entries:
        full_path = f"{path_prefix}/{entry.name}" if path_prefix else entry.name
        if entry_type(entry.mode) == "tree":
            flattened.extend(flatten_tree_to_entries(objects_dir, entry.oid, full_path))
        else:
            flattened.append(IndexEntry(path=full_path, mode=entry.mode, oid=entry.oid))
    return flattened