"""Tests for merge.py's orchestration: fast-forward, three-way merges,
merge-base search, conflict handling, and post-merge restoration.
"""

import pytest

from snapshot import checkout, commit, index, merge, objects, refs, repository, tree


def _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, path, content, message, timestamp):
    """Write a file, stage it, and commit the current full index state --
    mirroring what `snapshot add .` + `snapshot commit` would do.
    """
    file_path = repo_root / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    index.stage_file(objects_dir, index_path, repo_root, file_path)

    entries = index.read_index(index_path)
    tree_oid = tree.write_tree_from_index(objects_dir, entries)
    parent_oid = refs.resolve_head(snapshot_dir)
    new_commit = commit.build_commit(tree_oid, parent_oid, message, timestamp=timestamp)
    commit_oid = commit.store_commit(objects_dir, new_commit)
    refs.update_head(snapshot_dir, commit_oid)
    return commit_oid


def _setup(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    return snapshot_dir, snapshot_dir / "objects", snapshot_dir / "index", tmp_path


# --- Fast-forward -----------------------------------------------------


def test_fast_forward_moves_pointer_and_creates_no_new_objects(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v1", "c1", 1700500000)
    refs.create_branch(snapshot_dir, "feature")
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v2", "c2", 1700500100)
    c3 = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v3", "c3", 1700500200)

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    object_count_before = len(list(objects_dir.glob("*/*")))

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    object_count_after = len(list(objects_dir.glob("*/*")))

    assert result.kind == "fast_forward"
    assert result.commit_oid == c3
    assert refs.read_branch_oid(snapshot_dir / "refs" / "heads" / "main") == c3
    assert object_count_after == object_count_before


def test_fast_forward_restores_working_directory(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v1", "c1", 1700500300)
    refs.create_branch(snapshot_dir, "feature")
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v2", "c2", 1700500400)
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    assert (repo_root / "a.txt").read_text() == "v2"


def test_merge_already_up_to_date(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v1", "c1", 1700500500)
    refs.create_branch(snapshot_dir, "feature")

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    assert result.kind == "already_up_to_date"


def test_merge_already_up_to_date_when_target_behind(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v1", "c1", 1700500600)
    refs.create_branch(snapshot_dir, "feature")
    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v2", "c2", 1700500700)

    # main is now ahead of feature -- merging feature into main should be a no-op.
    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    assert result.kind == "already_up_to_date"


# --- Three-way merge ----------------------------------------------------


def test_three_way_merge_creates_commit_with_two_parents(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "README.md", "base\n", "base", 1700500800)
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    feature_oid = _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "README.md", "base\nfeature line\n", "feature work", 1700500900
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    main_oid = _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "main.py", "print('hi')\n", "main work", 1700501000
    )

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    assert result.kind == "merge_commit"
    merge_commit = commit.read_commit(objects_dir, result.commit_oid)
    assert merge_commit.parent == main_oid
    assert merge_commit.merge_parent == feature_oid
    assert merge_commit.message == "Merge feature into main"


def test_three_way_merge_stores_merged_tree_with_both_changes(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "README.md", "base\n", "base", 1700501100)
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "README.md", "base\nfeature line\n", "feature work", 1700501200
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "main.py", "print('hi')\n", "main work", 1700501300
    )

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    merge_commit = commit.read_commit(objects_dir, result.commit_oid)
    entries = tree.flatten_tree_to_entries(objects_dir, merge_commit.tree)
    paths_and_content = {}
    for entry in entries:
        _, content = objects.read_object(objects_dir, entry.oid)
        paths_and_content[entry.path] = content

    assert paths_and_content["README.md"] == b"base\nfeature line\n"
    assert paths_and_content["main.py"] == b"print('hi')\n"


def test_three_way_merge_updates_branch_ref(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "README.md", "base\n", "base", 1700501400)
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "b.txt", "feature", "feature work", 1700501500)

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "c.txt", "main", "main work", 1700501600)

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    assert refs.read_branch_oid(snapshot_dir / "refs" / "heads" / "main") == result.commit_oid


def test_non_overlapping_edits_merge_automatically(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "a.txt",
        "line1\nline2\nline3\nline4\nline5\n", "base", 1700501700,
    )
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "a.txt",
        "line1\nline2-FEATURE\nline3\nline4\nline5\n", "feature edit", 1700501800,
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "a.txt",
        "line1\nline2\nline3\nline4-MAIN\nline5\n", "main edit", 1700501900,
    )

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    assert result.kind == "merge_commit"
    assert (repo_root / "a.txt").read_text() == "line1\nline2-FEATURE\nline3\nline4-MAIN\nline5\n"


def test_working_directory_and_index_restored_after_successful_merge(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "README.md", "base\n", "base", 1700502000)
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "README.md", "base\nfeature line\n", "feature work", 1700502100
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "main.py", "print('hi')\n", "main work", 1700502200)

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    assert (repo_root / "README.md").read_text() == "base\nfeature line\n"
    assert (repo_root / "main.py").read_text() == "print('hi')\n"

    merge_commit = commit.read_commit(objects_dir, result.commit_oid)
    tree_entries = {e.path: e.oid for e in tree.flatten_tree_to_entries(objects_dir, merge_commit.tree)}
    index_entries = {e.path: e.oid for e in index.read_index(index_path)}
    assert index_entries == tree_entries


# --- Merge base -----------------------------------------------------------


def test_find_merge_base_on_linear_history(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    c1 = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v1", "c1", 1700502300)
    c2 = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v2", "c2", 1700502400)

    assert merge.find_merge_base(objects_dir, c1, c2) == c1


def test_find_merge_base_on_diverged_history(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    base = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "base", "base", 1700502500)
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    feature_tip = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "b.txt", "feature", "c2", 1700502600)

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    main_tip = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "c.txt", "main", "c3", 1700502700)

    assert merge.find_merge_base(objects_dir, main_tip, feature_tip) == base
    assert merge.find_merge_base(objects_dir, feature_tip, main_tip) == base  # symmetric


def test_find_merge_base_with_multiple_commits_each_side(tmp_path):
    """base -> c1, then (main: c2 -> c3) and (feature: c4 -> c5) diverge;
    c1 should remain the merge base regardless of how many commits pile
    up on each side.
    """
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    c1 = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "1", "c1", 1700502800)
    refs.create_branch(snapshot_dir, "feature")

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "main1.txt", "m1", "c2", 1700502900)
    main_tip = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "main2.txt", "m2", "c3", 1700503000)

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "feat1.txt", "f1", "c4", 1700503100)
    feature_tip = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "feat2.txt", "f2", "c5", 1700503200)

    assert merge.find_merge_base(objects_dir, main_tip, feature_tip) == c1


# --- Conflicts --------------------------------------------------------


def test_conflicting_merge_writes_markers_and_does_not_commit(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "line1\nline2\nline3\n", "base", 1700503300
    )
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "line1\nFEATURE-CHANGE\nline3\n", "feature edit", 1700503400
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    main_oid = _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "line1\nMAIN-CHANGE\nline3\n", "main edit", 1700503500
    )

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    assert result.kind == "conflict"
    assert result.conflicted_paths == ["a.txt"]

    content = (repo_root / "a.txt").read_text()
    assert "<<<<<<< HEAD" in content
    assert "MAIN-CHANGE" in content
    assert "=======" in content
    assert "FEATURE-CHANGE" in content
    assert ">>>>>>> feature" in content

    assert refs.read_branch_oid(snapshot_dir / "refs" / "heads" / "main") == main_oid


def test_conflicting_merge_does_not_modify_index(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "line1\nline2\nline3\n", "base", 1700503600
    )
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "line1\nFEATURE-CHANGE\nline3\n", "feature edit", 1700503700
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "line1\nMAIN-CHANGE\nline3\n", "main edit", 1700503800
    )

    entries_before = index.read_index(index_path)
    merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    entries_after = index.read_index(index_path)

    assert entries_before == entries_after


def test_conflicting_add_add_writes_whole_file_markers(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "README.md", "base\n", "base", 1700503900)
    refs.create_branch(snapshot_dir, "feature")

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "NOTES.md", "feature notes\n", "feature adds notes", 1700504000
    )

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    _write_and_commit(
        objects_dir, snapshot_dir, repo_root, index_path, "NOTES.md", "main notes\n", "main adds notes", 1700504100
    )

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")

    assert result.kind == "conflict"
    assert result.conflicted_paths == ["NOTES.md"]
    content = (repo_root / "NOTES.md").read_text()
    assert "main notes" in content
    assert "feature notes" in content


# --- Safety and validation ---------------------------------------------


def test_merge_refuses_with_uncommitted_changes(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)

    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v1", "c1", 1700504200)
    refs.create_branch(snapshot_dir, "feature")
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "b.txt", "v1", "c2", 1700504300)
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")

    (repo_root / "a.txt").write_text("dirty")

    with pytest.raises(ValueError):
        merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")


def test_merge_raises_for_nonexistent_branch(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)
    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v1", "c1", 1700504400)

    with pytest.raises(ValueError):
        merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "nope")


def test_merge_branch_into_itself_raises(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)
    _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v1", "c1", 1700504500)

    with pytest.raises(ValueError):
        merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")


def test_merge_raises_while_detached(tmp_path):
    snapshot_dir, objects_dir, index_path, repo_root = _setup(tmp_path)
    c1 = _write_and_commit(objects_dir, snapshot_dir, repo_root, index_path, "a.txt", "v1", "c1", 1700504600)
    refs.create_branch(snapshot_dir, "feature")
    checkout.checkout_commit(snapshot_dir, objects_dir, index_path, repo_root, c1)

    with pytest.raises(ValueError):
        merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")