import zlib
from pathlib import Path

import pytest

from snapshot import objects


def test_compute_oid_same_content_same_oid():
    oid1, _ = objects.compute_oid("blob", b"hello world")
    oid2, _ = objects.compute_oid("blob", b"hello world")
    assert oid1 == oid2


def test_compute_oid_different_content_different_oid():
    oid1, _ = objects.compute_oid("blob", b"hello world")
    oid2, _ = objects.compute_oid("blob", b"goodbye world")
    assert oid1 != oid2


def test_compute_oid_matches_real_git():
    # This is a well-known reference value: `git hash-object` on content
    # "hello world\n" produces this exact OID. Matching it confirms our
    # header format ("blob <size>\0<content>") is byte-for-byte what
    # real Git uses, not just "close enough".
    oid, full_data = objects.compute_oid("blob", b"hello world\n")
    assert full_data == b"blob 12\0hello world\n"
    assert oid == "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"


def test_object_path_uses_first_two_chars_as_directory():
    oid = "3b18e512dba79e4c8300dd08aeb37f8e728b8dad"
    path = objects.object_path(Path("/repo/.snapshot/objects"), oid)
    assert path == Path(
        "/repo/.snapshot/objects/3b/18e512dba79e4c8300dd08aeb37f8e728b8dad"
    )


def test_write_object_creates_file_at_correct_path(tmp_path):
    objects_dir = tmp_path / "objects"
    oid = objects.write_object(objects_dir, "blob", b"hello world")
    expected_path = objects.object_path(objects_dir, oid)
    assert expected_path.exists()


def test_write_object_stores_compressed_bytes(tmp_path):
    objects_dir = tmp_path / "objects"
    oid = objects.write_object(objects_dir, "blob", b"hello world")
    stored_bytes = objects.object_path(objects_dir, oid).read_bytes()

    # A successful zlib.decompress proves the bytes on disk are actually
    # compressed, not just the raw header + content written directly.
    decompressed = zlib.decompress(stored_bytes)
    assert decompressed == b"blob 11\0hello world"


def test_write_object_does_not_duplicate_identical_object(tmp_path):
    objects_dir = tmp_path / "objects"
    oid1 = objects.write_object(objects_dir, "blob", b"hello world")
    oid2 = objects.write_object(objects_dir, "blob", b"hello world")

    assert oid1 == oid2
    stored_files = list(objects_dir.glob("*/*"))
    assert len(stored_files) == 1


def test_read_object_round_trip(tmp_path):
    objects_dir = tmp_path / "objects"
    oid = objects.write_object(objects_dir, "blob", b"hello world")

    obj_type, content = objects.read_object(objects_dir, oid)

    assert obj_type == "blob"
    assert content == b"hello world"


def test_read_object_missing_oid_raises(tmp_path):
    objects_dir = tmp_path / "objects"
    objects_dir.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        objects.read_object(objects_dir, "0" * 40)