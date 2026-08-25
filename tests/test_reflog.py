from pathlib import Path

from snapshot import checkout, commit, index, merge, reflog, refs, tree
from snapshot.repository import init_repository


def _stage_file(objects_dir: Path, index_path: Path, repo_root: Path, name: str, content: str):
    path = repo_root / name
    path.write_text(content)
    return index.stage_file(objects_dir, index_path, repo_root, path)


def _commit(objects_dir: Path, index_path: Path, snapshot_dir: Path, message: str) -> str:
    entries = index.read_index(index_path)
    tree_oid = tree.write_tree_from_index(objects_dir, entries)
    parent_oid = refs.resolve_head(snapshot_dir)
    new_commit = commit.build_commit(tree_oid, parent_oid, message)
    commit_oid = commit.store_commit(objects_dir, new_commit)
    reflog_prefix = "commit (initial)" if parent_oid is None else "commit"
    refs.update_head(snapshot_dir, commit_oid, reflog_message=f"{reflog_prefix}: {message}")
    return commit_oid


def test_append_and_read_round_trip(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    reflog.append_entry(snapshot_dir, None, "a" * 40, "first entry")
    reflog.append_entry(snapshot_dir, "a" * 40, "b" * 40, "second entry")

    entries = reflog.read_entries(snapshot_dir)

    assert len(entries) == 2
    assert entries[0].old_oid == reflog.ZERO_OID  # None recorded as the zero sentinel
    assert entries[0].new_oid == "a" * 40
    assert entries[0].message == "first entry"
    assert entries[1].old_oid == "a" * 40
    assert entries[1].new_oid == "b" * 40
    assert entries[1].message == "second entry"  # oldest-first on disk


def test_read_entries_empty_when_nothing_recorded(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    assert reflog.read_entries(snapshot_dir) == []


def test_append_is_additive_not_overwriting(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    for i in range(5):
        reflog.append_entry(snapshot_dir, None, str(i) * 40, f"entry {i}")
    assert len(reflog.read_entries(snapshot_dir)) == 5


def test_commit_records_a_reflog_entry(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    _stage_file(objects_dir, index_path, tmp_path, "a.txt", "hello\n")
    commit_oid = _commit(objects_dir, index_path, snapshot_dir, "first commit")

    entries = reflog.read_entries(snapshot_dir)
    assert len(entries) == 1
    assert entries[0].old_oid == reflog.ZERO_OID
    assert entries[0].new_oid == commit_oid
    assert entries[0].message == "commit (initial): first commit"


def test_second_commit_records_old_oid_as_the_first_commit(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    _stage_file(objects_dir, index_path, tmp_path, "a.txt", "hello\n")
    first_oid = _commit(objects_dir, index_path, snapshot_dir, "first")
    _stage_file(objects_dir, index_path, tmp_path, "a.txt", "hello again\n")
    second_oid = _commit(objects_dir, index_path, snapshot_dir, "second")

    entries = reflog.read_entries(snapshot_dir)
    assert len(entries) == 2
    assert entries[1].old_oid == first_oid
    assert entries[1].new_oid == second_oid
    assert entries[1].message == "commit: second"


def test_checkout_branch_records_a_reflog_entry(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    _stage_file(objects_dir, index_path, tmp_path, "a.txt", "hello\n")
    base_oid = _commit(objects_dir, index_path, snapshot_dir, "base")
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, tmp_path, "feature")

    entries = reflog.read_entries(snapshot_dir)
    last = entries[-1]
    assert last.old_oid == base_oid
    assert last.new_oid == base_oid  # feature points at the same commit
    assert last.message == "checkout: moving from main to feature"


def test_checkout_commit_detach_records_a_reflog_entry(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    _stage_file(objects_dir, index_path, tmp_path, "a.txt", "hello\n")
    base_oid = _commit(objects_dir, index_path, snapshot_dir, "base")

    checkout.checkout_commit(snapshot_dir, objects_dir, index_path, tmp_path, base_oid)

    entries = reflog.read_entries(snapshot_dir)
    last = entries[-1]
    assert last.old_oid == base_oid
    assert last.new_oid == base_oid
    assert last.message == f"checkout: moving from main to {base_oid[:7]}"


def test_create_branch_does_not_move_head_so_no_reflog_entry(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    _stage_file(objects_dir, index_path, tmp_path, "a.txt", "hello\n")
    _commit(objects_dir, index_path, snapshot_dir, "base")
    before = len(reflog.read_entries(snapshot_dir))

    refs.create_branch(snapshot_dir, "feature")

    assert len(reflog.read_entries(snapshot_dir)) == before


def test_merge_fast_forward_records_a_reflog_entry(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    _stage_file(objects_dir, index_path, tmp_path, "a.txt", "one\n")
    _commit(objects_dir, index_path, snapshot_dir, "base")
    refs.create_branch(snapshot_dir, "feature")
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, tmp_path, "feature")
    _stage_file(objects_dir, index_path, tmp_path, "a.txt", "two\n")
    feature_oid = _commit(objects_dir, index_path, snapshot_dir, "on feature")
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, tmp_path, "main")

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, tmp_path, "feature")

    assert result.kind == "fast_forward"
    last = reflog.read_entries(snapshot_dir)[-1]
    assert last.new_oid == feature_oid
    assert last.message == "merge feature: Fast-forward"


def test_merge_commit_records_a_reflog_entry(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    _stage_file(objects_dir, index_path, tmp_path, "shared.txt", "base\n")
    _commit(objects_dir, index_path, snapshot_dir, "base")
    refs.create_branch(snapshot_dir, "feature")

    _stage_file(objects_dir, index_path, tmp_path, "main-only.txt", "x\n")
    _commit(objects_dir, index_path, snapshot_dir, "main change")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, tmp_path, "feature")
    _stage_file(objects_dir, index_path, tmp_path, "feature-only.txt", "y\n")
    _commit(objects_dir, index_path, snapshot_dir, "feature change")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, tmp_path, "main")
    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, tmp_path, "feature")

    assert result.kind == "merge_commit"
    last = reflog.read_entries(snapshot_dir)[-1]
    assert last.new_oid == result.commit_oid
    assert last.message == "merge feature: merge commit"


def test_merge_conflict_does_not_move_head_so_no_reflog_entry(tmp_path):
    snapshot_dir = init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    _stage_file(objects_dir, index_path, tmp_path, "f.txt", "base\n")
    _commit(objects_dir, index_path, snapshot_dir, "base")
    refs.create_branch(snapshot_dir, "feature")

    _stage_file(objects_dir, index_path, tmp_path, "f.txt", "main version\n")
    _commit(objects_dir, index_path, snapshot_dir, "main edits f")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, tmp_path, "feature")
    _stage_file(objects_dir, index_path, tmp_path, "f.txt", "feature version\n")
    _commit(objects_dir, index_path, snapshot_dir, "feature edits f")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, tmp_path, "main")
    before = len(reflog.read_entries(snapshot_dir))

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, tmp_path, "feature")

    assert result.kind == "conflict"
    assert len(reflog.read_entries(snapshot_dir)) == before
