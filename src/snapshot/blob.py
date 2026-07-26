"""Blob objects: Git's representation of file contents.

A blob stores exactly the bytes of a file's content -- nothing else.
The filename, permissions, and location are never part of a blob;
that information will later live in tree objects. This module is a
thin, blob-specific layer on top of the generic object store in
objects.py.
"""

from pathlib import Path

from . import objects


def compute_blob_oid(file_path: Path) -> str:
    """Compute the OID a file's contents would get as a blob, without storing it.

    Mirrors `git hash-object <file>` (no -w): useful for checking what
    OID something would have without touching the object database.
    """
    content = file_path.read_bytes()
    oid, _ = objects.compute_oid("blob", content)
    return oid


def store_blob(objects_dir: Path, file_path: Path) -> str:
    """Read a file and store its contents as a blob object. Returns the OID.

    Mirrors `git hash-object -w <file>`.
    """
    content = file_path.read_bytes()
    return objects.write_object(objects_dir, "blob", content)