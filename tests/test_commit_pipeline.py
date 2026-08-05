"""End-to-end tests that wire refs + tree + commit together the same way
`snapshot commit` does internally -- without going through the CLI.
"""

from snapshot import commit, index, objects, refs, repository, tree


def _commit_staged(objects_dir, snapshot_dir, entries, message, timestamp):
    """Mimic cmd_commit's pipeline: write tree, resolve parent, build+store
    commit, advance HEAD. Returns the new commit OID.

    Uses refs.update_head (Build #4) rather than manually reading/writing
    the branch ref, so this helper works correctly whether HEAD is
    symbolic or detached -- exactly like the real `snapshot commit`.
    """
    tree_oid = tree.write_tree_from_index(objects_dir, entries)
    parent_oid = refs.resolve_head(snapshot_dir)

    new_commit = commit.build_commit(tree_oid, parent_oid, message, timestamp=timestamp)
    commit_oid = commit.store_commit(objects_dir, new_commit)

    refs.update_head(snapshot_dir, commit_oid)
    return commit_oid


def test_first_commit_has_no_parent_and_creates_main(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    blob_oid = objects.write_object(objects_dir, "blob", b"hello")
    entries = [index.IndexEntry(path="README.md", mode="100644", oid=blob_oid)]

    main_ref_path = snapshot_dir / "refs" / "heads" / "main"
    assert not main_ref_path.exists()  # sanity check: absent before first commit

    commit_oid = _commit_staged(objects_dir, snapshot_dir, entries, "Initial commit", 1700001000)

    assert main_ref_path.exists()
    assert refs.read_branch_oid(main_ref_path) == commit_oid

    first_commit = commit.read_commit(objects_dir, commit_oid)
    assert first_commit.parent is None


def test_second_commit_links_to_first_as_parent(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"

    blob1 = objects.write_object(objects_dir, "blob", b"version 1")
    entries_v1 = [index.IndexEntry(path="README.md", mode="100644", oid=blob1)]
    first_oid = _commit_staged(objects_dir, snapshot_dir, entries_v1, "Initial commit", 1700001100)

    blob2 = objects.write_object(objects_dir, "blob", b"version 2")
    entries_v2 = [index.IndexEntry(path="README.md", mode="100644", oid=blob2)]
    second_oid = _commit_staged(objects_dir, snapshot_dir, entries_v2, "Update README", 1700001200)

    assert first_oid != second_oid

    second_commit = commit.read_commit(objects_dir, second_oid)
    assert second_commit.parent == first_oid


def test_main_ref_updates_to_latest_commit_each_time(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"
    main_ref_path = snapshot_dir / "refs" / "heads" / "main"

    blob1 = objects.write_object(objects_dir, "blob", b"v1")
    first_oid = _commit_staged(
        objects_dir, snapshot_dir,
        [index.IndexEntry(path="a.txt", mode="100644", oid=blob1)],
        "first", 1700001300,
    )
    assert refs.read_branch_oid(main_ref_path) == first_oid

    blob2 = objects.write_object(objects_dir, "blob", b"v2")
    second_oid = _commit_staged(
        objects_dir, snapshot_dir,
        [index.IndexEntry(path="a.txt", mode="100644", oid=blob2)],
        "second", 1700001400,
    )
    assert refs.read_branch_oid(main_ref_path) == second_oid
    assert refs.read_branch_oid(main_ref_path) != first_oid


def test_head_resolves_to_latest_commit(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"

    blob_oid = objects.write_object(objects_dir, "blob", b"content")
    commit_oid = _commit_staged(
        objects_dir, snapshot_dir,
        [index.IndexEntry(path="a.txt", mode="100644", oid=blob_oid)],
        "only commit", 1700001500,
    )

    assert refs.resolve_head(snapshot_dir) == commit_oid


def test_history_walk_via_parent_links_stops_at_initial_commit(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"

    oids = []
    for i in range(3):
        blob_oid = objects.write_object(objects_dir, "blob", f"v{i}".encode())
        oid = _commit_staged(
            objects_dir, snapshot_dir,
            [index.IndexEntry(path="a.txt", mode="100644", oid=blob_oid)],
            f"commit {i}", 1700001600 + i,
        )
        oids.append(oid)

    # Walk history from HEAD following parent links, like `snapshot log` does.
    walked = []
    current_oid = refs.resolve_head(snapshot_dir)
    while current_oid is not None:
        walked.append(current_oid)
        current_oid = commit.read_commit(objects_dir, current_oid).parent

    assert walked == list(reversed(oids))  # newest first, ending at the initial commit


def test_unrelated_unchanged_blob_reused_across_commits(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"

    shared_blob = objects.write_object(objects_dir, "blob", b"unchanging file")
    entries_v1 = [index.IndexEntry(path="README.md", mode="100644", oid=shared_blob)]
    _commit_staged(objects_dir, snapshot_dir, entries_v1, "first", 1700001700)

    blob_path = objects.object_path(objects_dir, shared_blob)
    mtime_before = blob_path.stat().st_mtime_ns

    new_blob = objects.write_object(objects_dir, "blob", b"a new file")
    entries_v2 = [
        index.IndexEntry(path="README.md", mode="100644", oid=shared_blob),
        index.IndexEntry(path="NOTES.md", mode="100644", oid=new_blob),
    ]
    _commit_staged(objects_dir, snapshot_dir, entries_v2, "second", 1700001800)

    assert blob_path.stat().st_mtime_ns == mtime_before  # never rewritten


# --- Build #4: committing while detached ---


def test_commit_while_detached_does_not_move_branch(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"

    blob1 = objects.write_object(objects_dir, "blob", b"v1")
    entries_v1 = [index.IndexEntry(path="a.txt", mode="100644", oid=blob1)]
    first_oid = _commit_staged(objects_dir, snapshot_dir, entries_v1, "first", 1700400000)

    main_ref_path = snapshot_dir / "refs" / "heads" / "main"
    assert refs.read_branch_oid(main_ref_path) == first_oid

    # Detach onto the commit that already exists.
    refs.set_detached_head(snapshot_dir, first_oid)
    assert refs.is_detached(snapshot_dir)

    # Commit again while detached, using the same pipeline `snapshot commit` uses.
    blob2 = objects.write_object(objects_dir, "blob", b"v2 detached")
    entries_v2 = [index.IndexEntry(path="a.txt", mode="100644", oid=blob2)]
    detached_oid = _commit_staged(objects_dir, snapshot_dir, entries_v2, "detached commit", 1700400100)

    # HEAD moved to the new detached commit...
    assert refs.resolve_head(snapshot_dir) == detached_oid
    assert refs.is_detached(snapshot_dir)
    assert refs.read_head(snapshot_dir) == detached_oid  # HEAD itself holds the new OID

    # ...but main's ref file is completely untouched.
    assert refs.read_branch_oid(main_ref_path) == first_oid


def test_detached_commit_still_links_to_its_parent(tmp_path):
    snapshot_dir = repository.init_repository(tmp_path)
    objects_dir = snapshot_dir / "objects"

    blob1 = objects.write_object(objects_dir, "blob", b"v1")
    entries_v1 = [index.IndexEntry(path="a.txt", mode="100644", oid=blob1)]
    first_oid = _commit_staged(objects_dir, snapshot_dir, entries_v1, "first", 1700400200)

    refs.set_detached_head(snapshot_dir, first_oid)

    blob2 = objects.write_object(objects_dir, "blob", b"v2")
    entries_v2 = [index.IndexEntry(path="a.txt", mode="100644", oid=blob2)]
    detached_oid = _commit_staged(objects_dir, snapshot_dir, entries_v2, "detached", 1700400300)

    detached_commit = commit.read_commit(objects_dir, detached_oid)
    assert detached_commit.parent == first_oid