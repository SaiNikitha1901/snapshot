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


# --- Build #4: detached HEAD ---


def test_is_detached_false_for_fresh_repo(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    assert refs.is_detached(snapshot_dir) is False


def test_is_detached_true_after_set_detached_head(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.set_detached_head(snapshot_dir, "a" * 40)
    assert refs.is_detached(snapshot_dir) is True


def test_set_detached_head_writes_raw_oid(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.set_detached_head(snapshot_dir, "b" * 40)
    assert refs.read_head(snapshot_dir) == "b" * 40


def test_resolve_head_returns_oid_directly_when_detached(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.set_detached_head(snapshot_dir, "c" * 40)
    assert refs.resolve_head(snapshot_dir) == "c" * 40


def test_set_symbolic_head_restores_branch_pointer(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.set_detached_head(snapshot_dir, "d" * 40)
    refs.set_symbolic_head(snapshot_dir, "main")
    assert refs.read_head(snapshot_dir) == "ref: refs/heads/main"
    assert refs.is_detached(snapshot_dir) is False


def test_current_branch_ref_path_raises_when_detached(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.set_detached_head(snapshot_dir, "e" * 40)
    with pytest.raises(ValueError):
        refs.current_branch_ref_path(snapshot_dir)


def test_current_branch_name_returns_active_branch(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    assert refs.current_branch_name(snapshot_dir) == "main"


def test_looks_like_oid():
    assert refs.looks_like_oid("a" * 40) is True
    assert refs.looks_like_oid("a" * 39) is False
    assert refs.looks_like_oid("not-an-oid") is False
    assert refs.looks_like_oid("A" * 40) is False  # uppercase not accepted


def test_update_head_updates_branch_ref_when_symbolic(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.update_head(snapshot_dir, "f" * 40)

    assert refs.read_head(snapshot_dir) == "ref: refs/heads/main"  # HEAD itself unchanged
    assert refs.read_branch_oid(snapshot_dir / "refs" / "heads" / "main") == "f" * 40


def test_update_head_overwrites_head_directly_when_detached(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.set_detached_head(snapshot_dir, "1" * 40)

    refs.update_head(snapshot_dir, "2" * 40)

    assert refs.read_head(snapshot_dir) == "2" * 40  # HEAD itself moved
    assert refs.is_detached(snapshot_dir)


# --- Build #4: branches ---


def test_list_branches_empty_when_none_created(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    assert refs.list_branches(snapshot_dir) == []


def test_list_branches_returns_sorted_names(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    for name in ["main", "feature", "experiment"]:
        refs.update_branch_ref(snapshot_dir / "refs" / "heads" / name, "a" * 40)

    assert refs.list_branches(snapshot_dir) == ["experiment", "feature", "main"]


def test_branch_exists(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    assert refs.branch_exists(snapshot_dir, "main") is False
    refs.update_branch_ref(snapshot_dir / "refs" / "heads" / "main", "a" * 40)
    assert refs.branch_exists(snapshot_dir, "main") is True


def test_create_branch_points_at_current_commit(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.update_branch_ref(snapshot_dir / "refs" / "heads" / "main", "a" * 40)

    oid = refs.create_branch(snapshot_dir, "feature")

    assert oid == "a" * 40
    assert refs.read_branch_oid(snapshot_dir / "refs" / "heads" / "feature") == "a" * 40


def test_create_branch_does_not_switch_head(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.update_branch_ref(snapshot_dir / "refs" / "heads" / "main", "a" * 40)

    refs.create_branch(snapshot_dir, "feature")

    assert refs.read_head(snapshot_dir) == "ref: refs/heads/main"  # still on main


def test_create_branch_raises_if_already_exists(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.update_branch_ref(snapshot_dir / "refs" / "heads" / "main", "a" * 40)
    refs.create_branch(snapshot_dir, "feature")

    with pytest.raises(ValueError):
        refs.create_branch(snapshot_dir, "feature")


def test_create_branch_raises_if_no_commits_yet(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    with pytest.raises(ValueError):
        refs.create_branch(snapshot_dir, "feature")


def test_create_branch_rejects_slash_in_name(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    refs.update_branch_ref(snapshot_dir / "refs" / "heads" / "main", "a" * 40)

    with pytest.raises(ValueError):
        refs.create_branch(snapshot_dir, "feature/sub")