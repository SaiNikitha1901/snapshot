from snapshot import blob, objects


def test_same_content_same_oid_regardless_of_filename(tmp_path):
    file1 = tmp_path / "a.txt"
    file2 = tmp_path / "b.txt"
    file1.write_text("identical content")
    file2.write_text("identical content")

    oid1 = blob.compute_blob_oid(file1)
    oid2 = blob.compute_blob_oid(file2)

    assert oid1 == oid2  # filename must not affect the blob OID


def test_different_content_different_oid(tmp_path):
    file1 = tmp_path / "a.txt"
    file2 = tmp_path / "b.txt"
    file1.write_text("content A")
    file2.write_text("content B")

    assert blob.compute_blob_oid(file1) != blob.compute_blob_oid(file2)


def test_compute_blob_oid_does_not_write_anything(tmp_path):
    file_path = tmp_path / "a.txt"
    file_path.write_text("hello")
    objects_dir = tmp_path / "objects"

    blob.compute_blob_oid(file_path)

    assert not objects_dir.exists()


def test_store_blob_writes_and_returns_matching_oid(tmp_path):
    file_path = tmp_path / "a.txt"
    file_path.write_text("hello")
    objects_dir = tmp_path / "objects"

    expected_oid = blob.compute_blob_oid(file_path)
    stored_oid = blob.store_blob(objects_dir, file_path)

    assert stored_oid == expected_oid
    assert objects.object_path(objects_dir, stored_oid).exists()


def test_store_blob_content_round_trips(tmp_path):
    file_path = tmp_path / "a.txt"
    file_path.write_text("round trip me")
    objects_dir = tmp_path / "objects"

    oid = blob.store_blob(objects_dir, file_path)
    obj_type, content = objects.read_object(objects_dir, oid)

    assert obj_type == "blob"
    assert content == b"round trip me"