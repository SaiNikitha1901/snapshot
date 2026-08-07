import pytest

from snapshot import commit, objects


def test_build_commit_without_parent():
    c = commit.build_commit("t" * 40, None, "Initial commit", timestamp=1700000000)
    assert c.tree == "t" * 40
    assert c.parent is None
    assert c.message == "Initial commit"
    assert "1700000000" in c.author
    assert c.author == c.committer


def test_encode_commit_omits_parent_line_for_first_commit():
    c = commit.build_commit("t" * 40, None, "Initial commit", timestamp=1700000000)
    payload = commit.encode_commit(c)
    text = payload.decode()

    assert text.startswith(f"tree {'t' * 40}\n")
    assert "parent" not in text
    assert text.endswith("\n\nInitial commit")


def test_encode_commit_includes_parent_line_when_present():
    c = commit.build_commit("t" * 40, "p" * 40, "Second commit", timestamp=1700000100)
    payload = commit.encode_commit(c)
    text = payload.decode()

    assert f"parent {'p' * 40}" in text


def test_commit_encode_decode_round_trip():
    original = commit.build_commit("t" * 40, "p" * 40, "A commit message", timestamp=1700000200)
    payload = commit.encode_commit(original)
    decoded = commit.decode_commit(payload)

    assert decoded == original


def test_commit_message_preserved_through_round_trip():
    original = commit.build_commit("t" * 40, None, "Multi-line\n\nmessage body", timestamp=1700000300)
    decoded = commit.decode_commit(commit.encode_commit(original))

    assert decoded.message == "Multi-line\n\nmessage body"


def test_commit_author_and_committer_preserved():
    original = commit.build_commit("t" * 40, None, "msg", timestamp=1700000400)
    decoded = commit.decode_commit(commit.encode_commit(original))

    assert decoded.author == original.author
    assert decoded.committer == original.committer


def test_decode_commit_missing_tree_header_raises():
    payload = (
        b"author Snapshot User <snapshot@example.com> 1700000000\n"
        b"committer Snapshot User <snapshot@example.com> 1700000000\n"
        b"\nmsg"
    )
    with pytest.raises(ValueError):
        commit.decode_commit(payload)


def test_decode_commit_missing_blank_line_raises():
    payload = b"tree " + b"t" * 40 + b"\nauthor a\ncommitter a\nno blank line here"
    with pytest.raises(ValueError):
        commit.decode_commit(payload)


def test_decode_commit_unrecognized_header_raises():
    payload = b"tree " + b"t" * 40 + b"\nbogus-header value\nauthor a\ncommitter a\n\nmsg"
    with pytest.raises(ValueError):
        commit.decode_commit(payload)


def test_store_commit_uses_generic_object_layer(tmp_path):
    objects_dir = tmp_path / "objects"
    c = commit.build_commit("t" * 40, None, "msg", timestamp=1700000500)

    oid = commit.store_commit(objects_dir, c)

    obj_type, payload = objects.read_object(objects_dir, oid)
    assert obj_type == "commit"
    assert commit.decode_commit(payload) == c


def test_read_commit_round_trips_through_storage(tmp_path):
    objects_dir = tmp_path / "objects"
    c = commit.build_commit("t" * 40, None, "msg", timestamp=1700000600)
    oid = commit.store_commit(objects_dir, c)

    read_back = commit.read_commit(objects_dir, oid)

    assert read_back == c


def test_read_commit_rejects_non_commit_object(tmp_path):
    objects_dir = tmp_path / "objects"
    blob_oid = objects.write_object(objects_dir, "blob", b"not a commit")

    with pytest.raises(ValueError):
        commit.read_commit(objects_dir, blob_oid)


# --- Build #5: merge commits (second parent) ---


def test_regular_commit_has_no_merge_parent():
    c = commit.build_commit("t" * 40, None, "Initial", timestamp=1700600000)
    assert c.merge_parent is None


def test_build_commit_with_merge_parent():
    c = commit.build_commit(
        "t" * 40, "p" * 40, "Merge x into y", timestamp=1700600100, merge_parent_oid="q" * 40
    )
    assert c.parent == "p" * 40
    assert c.merge_parent == "q" * 40


def test_encode_commit_includes_both_parent_lines_for_merge_commit():
    c = commit.build_commit(
        "t" * 40, "p" * 40, "Merge", timestamp=1700600200, merge_parent_oid="q" * 40
    )
    text = commit.encode_commit(c).decode()
    assert f"parent {'p' * 40}" in text
    assert f"parent {'q' * 40}" in text
    assert text.count("parent ") == 2


def test_merge_commit_round_trips():
    original = commit.build_commit(
        "t" * 40, "p" * 40, "Merge", timestamp=1700600300, merge_parent_oid="q" * 40
    )
    decoded = commit.decode_commit(commit.encode_commit(original))
    assert decoded == original
    assert decoded.merge_parent == "q" * 40


def test_decode_commit_rejects_more_than_two_parents():
    payload = (
        b"tree " + b"t" * 40 + b"\n"
        b"parent " + b"1" * 40 + b"\n"
        b"parent " + b"2" * 40 + b"\n"
        b"parent " + b"3" * 40 + b"\n"
        b"author a\ncommitter a\n\nmsg"
    )
    with pytest.raises(ValueError):
        commit.decode_commit(payload)