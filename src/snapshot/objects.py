"""Generic content-addressable object storage.

This module knows nothing about blobs, trees, or commits specifically.
It only knows how to take a (type, content) pair, hash it the way Git
does, and store/retrieve the result as a compressed loose object.
Blob, tree, and commit modules will all build on top of this.
"""

import hashlib
import zlib
from pathlib import Path


def compute_oid(obj_type: str, content: bytes) -> tuple[str, bytes]:
    """Build the Git-style object representation and hash it.

    Git's object format is: "<type> <size>\\0<content>"
    The OID is the SHA-1 hex digest of that *entire* byte string,
    header included, not just the raw content.

    Returns:
        (oid, full_object_bytes) -- the hex OID and the exact bytes
        that were hashed, so callers can write them without redoing
        the header construction.
    """
    header = f"{obj_type} {len(content)}\0".encode()
    full_data = header + content
    oid = hashlib.sha1(full_data).hexdigest()
    return oid, full_data


def object_path(objects_dir: Path, oid: str) -> Path:
    """Map an OID to its on-disk location: objects/xx/yyyy...

    The first two hex characters become a subdirectory so a single
    directory never ends up with tens of thousands of files. This is
    purely a filesystem-performance convention -- it has no effect on
    the OID itself.
    """
    return objects_dir / oid[:2] / oid[2:]


def write_object(objects_dir: Path, obj_type: str, content: bytes) -> str:
    """Store (type, content) as a compressed loose object. Returns its OID.

    Because storage is content-addressed, writing the same (type, content)
    twice is a no-op the second time: the OID is identical, so the
    existing file is reused instead of being rewritten.
    """
    oid, full_data = compute_oid(obj_type, content)
    path = object_path(objects_dir, oid)

    if path.exists():
        return oid

    path.parent.mkdir(parents=True, exist_ok=True)
    compressed = zlib.compress(full_data)
    path.write_bytes(compressed)
    return oid


def read_object(objects_dir: Path, oid: str) -> tuple[str, bytes]:
    """Read and decode a stored object by its OID.

    Returns:
        (obj_type, content) -- the object's type string and its raw
        content bytes, with the header stripped off.

    Raises:
        FileNotFoundError: no object exists for this OID.
        ValueError: the stored bytes are malformed (not a valid
            "<type> <size>\\0<content>" object after decompression).
    """
    path = object_path(objects_dir, oid)
    if not path.exists():
        raise FileNotFoundError(f"no object found for OID {oid}")

    compressed = path.read_bytes()
    full_data = zlib.decompress(compressed)

    if b"\0" not in full_data:
        raise ValueError(f"object {oid} is malformed: missing header separator")

    header, _, content = full_data.partition(b"\0")

    try:
        obj_type, size_str = header.decode().split(" ", 1)
        expected_size = int(size_str)
    except ValueError as exc:
        raise ValueError(f"object {oid} has a malformed header: {header!r}") from exc

    if expected_size != len(content):
        raise ValueError(
            f"object {oid} is corrupt: header says {expected_size} bytes, "
            f"but content is {len(content)} bytes"
        )

    return obj_type, content