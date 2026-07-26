from pathlib import Path

import pytest

from snapshot import index, objects, tree


def _entry(path, oid, mode="100644"):
    return index.IndexEntry(path=path, mode=mode, oid=oid)


def test_single_file_index_produces_valid_root_tree(tmp_path):
    objects_dir = tmp_path / "objects"
    blob_oid = objects.write_object(objects_dir, "blob", b"hello")
    entries = [_entry("README.md", blob_oid)]

    root_oid = tree.write_tree_from_index(objects_dir, entries)

    obj_type, payload = objects.read_object(objects_dir, root_oid)
    assert obj_type == "tree"

    decoded = tree.decode_tree_payload(payload)
    assert len(decoded) == 1
    assert decoded[0].name == "README.md"
    assert decoded[0].oid == blob_oid
    assert decoded[0].mode == "100644"


def test_nested_path_creates_subtree(tmp_path):
    objects_dir = tmp_path / "objects"
    blob_a = objects.write_object(objects_dir, "blob", b"content A")
    blob_b = objects.write_object(objects_dir, "blob", b"content B")
    entries = [
        _entry("README.md", blob_a),
        _entry("src/main.py", blob_b),
    ]

    root_oid = tree.write_tree_from_index(objects_dir, entries)
    _, root_payload = objects.read_object(objects_dir, root_oid)
    root_entries = {e.name: e for e in tree.decode_tree_payload(root_payload)}

    assert "README.md" in root_entries
    assert "src" in root_entries
    assert root_entries["src"].mode == "40000"
    assert tree.entry_type(root_entries["src"].mode) == "tree"

    subtree_oid = root_entries["src"].oid
    _, subtree_payload = objects.read_object(objects_dir, subtree_oid)
    subtree_entries = {e.name: e for e in tree.decode_tree_payload(subtree_payload)}

    assert subtree_entries["main.py"].oid == blob_b
    assert tree.entry_type(subtree_entries["main.py"].mode) == "blob"


def test_tree_payload_uses_raw_20_byte_oids():
    entry = tree.TreeEntry(mode="100644", name="a.txt", oid="a" * 40)
    encoded = tree.encode_tree_entry(entry)

    header = b"100644 a.txt\0"
    assert encoded == header + bytes.fromhex("a" * 40)
    assert len(encoded) == len(header) + 20


def test_tree_encoding_decoding_round_trip():
    entries = [
        tree.TreeEntry(mode="100644", name="README.md", oid="1" * 40),
        tree.TreeEntry(mode="40000", name="src", oid="2" * 40),
        tree.TreeEntry(mode="100755", name="run.sh", oid="3" * 40),
    ]
    payload = tree.encode_tree(entries)
    decoded = tree.decode_tree_payload(payload)

    decoded_by_name = {e.name: e for e in decoded}
    assert decoded_by_name["README.md"].oid == "1" * 40
    assert decoded_by_name["README.md"].mode == "100644"
    assert decoded_by_name["src"].mode == "40000"
    assert decoded_by_name["run.sh"].mode == "100755"


def test_directory_mode_has_no_leading_zero_when_encoded():
    entry = tree.TreeEntry(mode="40000", name="src", oid="a" * 40)
    encoded = tree.encode_tree_entry(entry)

    assert encoded.startswith(b"40000 src\0")  # not "040000"


def test_ls_tree_distinguishes_blob_and_tree_entries():
    entries = [
        tree.TreeEntry(mode="100644", name="README.md", oid="1" * 40),
        tree.TreeEntry(mode="40000", name="src", oid="2" * 40),
    ]
    types = {e.name: tree.entry_type(e.mode) for e in entries}

    assert types["README.md"] == "blob"
    assert types["src"] == "tree"


def test_unchanged_subtree_gets_same_oid_across_writes(tmp_path):
    objects_dir = tmp_path / "objects"
    blob_a = objects.write_object(objects_dir, "blob", b"a content")
    blob_b = objects.write_object(objects_dir, "blob", b"b content")
    entries_v1 = [
        _entry("README.md", blob_a),
        _entry("src/utils.py", blob_b),
    ]

    root_oid_v1 = tree.write_tree_from_index(objects_dir, entries_v1)
    _, payload_v1 = objects.read_object(objects_dir, root_oid_v1)
    subtree_oid_v1 = {e.name: e.oid for e in tree.decode_tree_payload(payload_v1)}["src"]

    # Change only the root-level file; the "src" subtree's contents don't change.
    blob_a2 = objects.write_object(objects_dir, "blob", b"a content v2")
    entries_v2 = [
        _entry("README.md", blob_a2),
        _entry("src/utils.py", blob_b),
    ]

    root_oid_v2 = tree.write_tree_from_index(objects_dir, entries_v2)
    _, payload_v2 = objects.read_object(objects_dir, root_oid_v2)
    subtree_oid_v2 = {e.name: e.oid for e in tree.decode_tree_payload(payload_v2)}["src"]

    assert root_oid_v1 != root_oid_v2  # root changed (README.md changed)
    assert subtree_oid_v1 == subtree_oid_v2  # unchanged subtree reused


def test_changing_file_in_subtree_changes_subtree_oid(tmp_path):
    objects_dir = tmp_path / "objects"
    blob_a = objects.write_object(objects_dir, "blob", b"unchanged root file")
    blob_b1 = objects.write_object(objects_dir, "blob", b"utils v1")

    entries_v1 = [_entry("README.md", blob_a), _entry("src/utils.py", blob_b1)]
    root_oid_v1 = tree.write_tree_from_index(objects_dir, entries_v1)
    _, payload_v1 = objects.read_object(objects_dir, root_oid_v1)
    subtree_oid_v1 = {e.name: e.oid for e in tree.decode_tree_payload(payload_v1)}["src"]

    blob_b2 = objects.write_object(objects_dir, "blob", b"utils v2")
    entries_v2 = [_entry("README.md", blob_a), _entry("src/utils.py", blob_b2)]
    root_oid_v2 = tree.write_tree_from_index(objects_dir, entries_v2)
    _, payload_v2 = objects.read_object(objects_dir, root_oid_v2)
    subtree_oid_v2 = {e.name: e.oid for e in tree.decode_tree_payload(payload_v2)}["src"]

    assert subtree_oid_v1 != subtree_oid_v2


def test_unrelated_unchanged_blobs_remain_reused(tmp_path):
    objects_dir = tmp_path / "objects"
    shared_blob = objects.write_object(objects_dir, "blob", b"shared content")

    entries_v1 = [_entry("README.md", shared_blob)]
    tree.write_tree_from_index(objects_dir, entries_v1)

    blob_path = objects.object_path(objects_dir, shared_blob)
    mtime_before = blob_path.stat().st_mtime_ns

    entries_v2 = [_entry("README.md", shared_blob), _entry("NOTES.md", shared_blob)]
    tree.write_tree_from_index(objects_dir, entries_v2)

    mtime_after = blob_path.stat().st_mtime_ns

    assert blob_path.exists()
    assert mtime_before == mtime_after  # the shared blob file was never rewritten


def test_write_tree_from_empty_index_raises():
    objects_dir_placeholder = Path("/unused")  # never touched; error raised before any I/O
    with pytest.raises(ValueError):
        tree.write_tree_from_index(objects_dir_placeholder, [])


def test_tree_object_read_through_objects_module_reports_type_tree(tmp_path):
    objects_dir = tmp_path / "objects"
    blob_oid = objects.write_object(objects_dir, "blob", b"content")
    entries = [_entry("a.txt", blob_oid)]

    root_oid = tree.write_tree_from_index(objects_dir, entries)
    obj_type, _ = objects.read_object(objects_dir, root_oid)

    assert obj_type == "tree"


def test_write_tree_preserves_executable_mode(tmp_path):
    objects_dir = tmp_path / "objects"
    blob_oid = objects.write_object(objects_dir, "blob", b"#!/bin/sh\necho hi\n")
    entries = [_entry("run.sh", blob_oid, mode="100755")]

    root_oid = tree.write_tree_from_index(objects_dir, entries)
    _, payload = objects.read_object(objects_dir, root_oid)
    decoded = {e.name: e for e in tree.decode_tree_payload(payload)}

    assert decoded["run.sh"].mode == "100755"