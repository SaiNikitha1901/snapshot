import stat

import pytest

from snapshot import blob, index, objects


def test_stage_file_creates_and_stores_blob(tmp_path):
    objects_dir = tmp_path / ".snapshot" / "objects"
    index_path = tmp_path / ".snapshot" / "index"
    file_path = tmp_path / "README.md"
    file_path.write_text("hello project")

    entry = index.stage_file(objects_dir, index_path, tmp_path, file_path)

    obj_type, content = objects.read_object(objects_dir, entry.oid)
    assert obj_type == "blob"
    assert content == b"hello project"


def test_stage_file_records_repo_relative_path(tmp_path):
    objects_dir = tmp_path / ".snapshot" / "objects"
    index_path = tmp_path / ".snapshot" / "index"
    (tmp_path / "src").mkdir()
    file_path = tmp_path / "src" / "main.py"
    file_path.write_text("print('hi')")

    entry = index.stage_file(objects_dir, index_path, tmp_path, file_path)

    assert entry.path == "src/main.py"


def test_stage_file_records_correct_blob_oid(tmp_path):
    objects_dir = tmp_path / ".snapshot" / "objects"
    index_path = tmp_path / ".snapshot" / "index"
    file_path = tmp_path / "a.txt"
    file_path.write_text("some content")

    expected_oid = blob.compute_blob_oid(file_path)
    entry = index.stage_file(objects_dir, index_path, tmp_path, file_path)

    assert entry.oid == expected_oid


def test_staging_unchanged_file_again_does_not_duplicate_blob(tmp_path):
    objects_dir = tmp_path / ".snapshot" / "objects"
    index_path = tmp_path / ".snapshot" / "index"
    file_path = tmp_path / "a.txt"
    file_path.write_text("same content")

    index.stage_file(objects_dir, index_path, tmp_path, file_path)
    index.stage_file(objects_dir, index_path, tmp_path, file_path)

    stored_files = list(objects_dir.glob("*/*"))
    assert len(stored_files) == 1

    entries = index.read_index(index_path)
    assert len(entries) == 1  # re-staging updates the entry, doesn't duplicate it


def test_staging_modified_file_updates_index_oid(tmp_path):
    objects_dir = tmp_path / ".snapshot" / "objects"
    index_path = tmp_path / ".snapshot" / "index"
    file_path = tmp_path / "a.txt"

    file_path.write_text("version one")
    entry_v1 = index.stage_file(objects_dir, index_path, tmp_path, file_path)

    file_path.write_text("version two")
    entry_v2 = index.stage_file(objects_dir, index_path, tmp_path, file_path)

    assert entry_v1.oid != entry_v2.oid

    entries = index.read_index(index_path)
    assert len(entries) == 1
    assert entries[0].oid == entry_v2.oid


def test_different_filenames_same_content_share_blob_but_differ_in_path(tmp_path):
    objects_dir = tmp_path / ".snapshot" / "objects"
    index_path = tmp_path / ".snapshot" / "index"
    file1 = tmp_path / "a.txt"
    file2 = tmp_path / "b.txt"
    file1.write_text("identical content")
    file2.write_text("identical content")

    entry1 = index.stage_file(objects_dir, index_path, tmp_path, file1)
    entry2 = index.stage_file(objects_dir, index_path, tmp_path, file2)

    assert entry1.oid == entry2.oid  # same blob
    assert entry1.path != entry2.path  # different index paths

    entries = index.read_index(index_path)
    assert len(entries) == 2


def test_stage_file_outside_repo_raises(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    objects_dir = repo_root / ".snapshot" / "objects"
    index_path = repo_root / ".snapshot" / "index"
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("nope")

    with pytest.raises(ValueError):
        index.stage_file(objects_dir, index_path, repo_root, outside_file)


def test_write_and_read_index_round_trip(tmp_path):
    index_path = tmp_path / "index"
    entries = [
        index.IndexEntry(path="b.txt", mode="100644", oid="b" * 40),
        index.IndexEntry(path="a.txt", mode="100644", oid="a" * 40),
    ]
    index.write_index(index_path, entries)

    result = index.read_index(index_path)

    assert [e.path for e in result] == ["a.txt", "b.txt"]  # sorted


def test_read_index_missing_file_returns_empty_list(tmp_path):
    index_path = tmp_path / "index"
    assert index.read_index(index_path) == []


def test_collect_stageable_files_skips_snapshot_dir(tmp_path):
    (tmp_path / ".snapshot" / "objects").mkdir(parents=True)
    (tmp_path / ".snapshot" / "objects" / "junk").write_text("x")
    (tmp_path / "README.md").write_text("hi")

    files = index.collect_stageable_files(tmp_path)

    assert tmp_path / "README.md" in files
    assert not any(".snapshot" in f.parts for f in files)


def test_file_mode_detects_executable(tmp_path):
    file_path = tmp_path / "script.sh"
    file_path.write_text("#!/bin/sh\necho hi\n")
    file_path.chmod(file_path.stat().st_mode | stat.S_IXUSR)

    assert index.file_mode(file_path) == "100755"


def test_file_mode_defaults_to_regular(tmp_path):
    file_path = tmp_path / "plain.txt"
    file_path.write_text("just text")

    assert index.file_mode(file_path) == "100644"