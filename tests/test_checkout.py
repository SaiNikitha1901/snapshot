"""Tests for checkout.py: branch switching, detached HEAD, and safe-checkout refusal."""

import pytest

from snapshot import blob, checkout, commit, index, objects, refs, repository, tree


def _write_file(repo_root, rel_path, content):
    file_path = repo_root / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    return file_path


def _commit_all(objects_dir, snapshot_dir, entries, message, timestamp):
    """Same small pipeline used elsewhere: write tree, resolve parent,
    build+store commit, advance HEAD (branch ref, or HEAD itself if detached).
    """
    tree_oid = tree.write_tree_from_index(objects_dir, entries)
    parent_oid = refs.resolve_head(snapshot_dir)
    new_commit = commit.build_commit(tree_oid, parent_oid, message, timestamp=timestamp)
    commit_oid = commit.store_commit(objects_dir, new_commit)
    refs.update_head(snapshot_dir, commit_oid)
    return commit_oid


def _setup_repo_with_two_branches(tmp_path):
    """main has README.md = "v1 main"; feature branches off main then
    changes README.md to "v1 feature". Leaves HEAD on feature.

    Returns (snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid).
    """
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = tmp_path

    readme = _write_file(repo_root, "README.md", "v1 main")
    entry = index.stage_file(objects_dir, index_path, repo_root, readme)
    main_oid = _commit_all(objects_dir, snapshot_dir, [entry], "main commit", 1700100000)

    refs.create_branch(snapshot_dir, "feature")
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    _write_file(repo_root, "README.md", "v1 feature")
    entry2 = index.stage_file(objects_dir, index_path, repo_root, readme)
    feature_oid = _commit_all(objects_dir, snapshot_dir, [entry2], "feature commit", 1700100100)

    return snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid


def test_checkout_branch_restores_working_directory(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid = (
        _setup_repo_with_two_branches(tmp_path)
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    assert (repo_root / "README.md").read_text() == "v1 main"


def test_checkout_branch_restores_index(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid = (
        _setup_repo_with_two_branches(tmp_path)
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    entries = index.read_index(index_path)
    assert len(entries) == 1
    readme_blob_oid = blob.compute_blob_oid(repo_root / "README.md")
    assert entries[0].oid == readme_blob_oid


def test_checkout_branch_updates_head_symbolically(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid = (
        _setup_repo_with_two_branches(tmp_path)
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    assert refs.read_head(snapshot_dir) == "ref: refs/heads/main"
    assert not refs.is_detached(snapshot_dir)


def test_checkout_removes_files_absent_from_target_tree(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = tmp_path

    readme = _write_file(repo_root, "README.md", "hello")
    entry = index.stage_file(objects_dir, index_path, repo_root, readme)
    _commit_all(objects_dir, snapshot_dir, [entry], "first", 1700200000)

    refs.create_branch(snapshot_dir, "feature")
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    extra = _write_file(repo_root, "extra.txt", "only on feature")
    entry_readme = index.stage_file(objects_dir, index_path, repo_root, readme)
    entry_extra = index.stage_file(objects_dir, index_path, repo_root, extra)
    _commit_all(
        objects_dir, snapshot_dir, [entry_readme, entry_extra],
        "feature adds extra.txt", 1700200100,
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    assert (repo_root / "README.md").exists()
    assert not (repo_root / "extra.txt").exists()  # feature-only file removed


def test_checkout_commit_detaches_head(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid = (
        _setup_repo_with_two_branches(tmp_path)
    )
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    checkout.checkout_commit(snapshot_dir, objects_dir, index_path, repo_root, feature_oid)

    assert refs.is_detached(snapshot_dir)
    assert refs.read_head(snapshot_dir) == feature_oid
    assert (repo_root / "README.md").read_text() == "v1 feature"


def test_checkout_commit_raises_for_unknown_target(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = tmp_path

    with pytest.raises(ValueError):
        checkout.checkout_commit(snapshot_dir, objects_dir, index_path, repo_root, "0" * 40)


def test_checkout_commit_raises_for_malformed_target(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = tmp_path

    with pytest.raises(ValueError):
        checkout.checkout_commit(snapshot_dir, objects_dir, index_path, repo_root, "not-an-oid")


def test_checkout_commit_raises_for_non_commit_object(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = tmp_path

    blob_oid = objects.write_object(objects_dir, "blob", b"not a commit")

    with pytest.raises(ValueError):
        checkout.checkout_commit(snapshot_dir, objects_dir, index_path, repo_root, blob_oid)


def test_checkout_branch_raises_for_unknown_branch(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = tmp_path

    with pytest.raises(ValueError):
        checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "nope")


def test_checkout_refuses_with_unstaged_changes(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid = (
        _setup_repo_with_two_branches(tmp_path)
    )
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    (repo_root / "README.md").write_text("dirty, unstaged edit")  # not re-staged

    with pytest.raises(ValueError):
        checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")


def test_checkout_refuses_with_staged_changes(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid = (
        _setup_repo_with_two_branches(tmp_path)
    )
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    (repo_root / "README.md").write_text("staged edit")
    index.stage_file(objects_dir, index_path, repo_root, repo_root / "README.md")

    with pytest.raises(ValueError):
        checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")


def test_checkout_refuses_with_mixed_staged_and_unstaged_changes(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid = (
        _setup_repo_with_two_branches(tmp_path)
    )
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    (repo_root / "README.md").write_text("staged edit")
    index.stage_file(objects_dir, index_path, repo_root, repo_root / "README.md")
    (repo_root / "README.md").write_text("further unstaged edit on top")

    with pytest.raises(ValueError):
        checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")


def test_checkout_succeeds_when_clean(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root, main_oid, feature_oid = (
        _setup_repo_with_two_branches(tmp_path)
    )
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    # No modifications made since checking out main -- should succeed.
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    assert (repo_root / "README.md").read_text() == "v1 feature"


def test_unstaged_changes_exist_detects_deleted_tracked_file(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = tmp_path

    readme = _write_file(repo_root, "README.md", "hello")
    entry = index.stage_file(objects_dir, index_path, repo_root, readme)
    _commit_all(objects_dir, snapshot_dir, [entry], "first", 1700300000)

    assert not checkout.unstaged_changes_exist(repo_root, index_path)

    readme.unlink()

    assert checkout.unstaged_changes_exist(repo_root, index_path)


def test_staged_changes_exist_true_before_first_commit(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = tmp_path

    readme = _write_file(repo_root, "README.md", "hello")
    index.stage_file(objects_dir, index_path, repo_root, readme)

    assert checkout.staged_changes_exist(objects_dir, index_path, None)