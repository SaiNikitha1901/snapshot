import pytest

from snapshot import refs, repository


def test_read_head_returns_raw_contents(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    assert refs.read_head(snapshot_dir) == "ref: refs/heads/main"


def test_current_branch_ref_path_resolves_symbolic_head(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    ref_path = refs.current_branch_ref_path(snapshot_dir)
    assert ref_path == snapshot_dir / "refs" / "heads" / "main"


def test_current_branch_ref_path_raises_on_malformed_head(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    (snapshot_dir / "HEAD").write_text("not-a-valid-ref-line\n")

    with pytest.raises(ValueError):
        refs.current_branch_ref_path(snapshot_dir)


def test_current_branch_ref_path_raises_when_head_missing(tmp_path):
    snapshot_dir = tmp_path / ".snapshot"
    snapshot_dir.mkdir()

    with pytest.raises(ValueError):
        refs.current_branch_ref_path(snapshot_dir)


def test_read_branch_oid_returns_none_when_ref_missing(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    ref_path = refs.current_branch_ref_path(snapshot_dir)

    assert refs.read_branch_oid(ref_path) is None


def test_resolve_head_returns_none_before_first_commit(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    assert refs.resolve_head(snapshot_dir) is None


def test_update_branch_ref_creates_file_and_parents(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    ref_path = refs.current_branch_ref_path(snapshot_dir)
    fake_oid = "a" * 40

    refs.update_branch_ref(ref_path, fake_oid)

    assert ref_path.exists()
    assert refs.read_branch_oid(ref_path) == fake_oid


def test_resolve_head_returns_oid_after_ref_updated(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    ref_path = refs.current_branch_ref_path(snapshot_dir)
    fake_oid = "b" * 40
    refs.update_branch_ref(ref_path, fake_oid)

    assert refs.resolve_head(snapshot_dir) == fake_oid


def test_update_branch_ref_overwrites_previous_oid(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    ref_path = refs.current_branch_ref_path(snapshot_dir)

    refs.update_branch_ref(ref_path, "a" * 40)
    refs.update_branch_ref(ref_path, "b" * 40)

    assert refs.read_branch_oid(ref_path) == "b" * 40