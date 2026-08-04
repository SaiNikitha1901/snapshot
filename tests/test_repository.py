from snapshot import repository


def test_init_creates_objects_directory(tmp_path):
    repository.init_repository(tmp_path)
    assert (tmp_path / ".snapshot" / "objects").is_dir()


def test_init_creates_head_file(tmp_path):
    repository.init_repository(tmp_path)
    head_path = tmp_path / ".snapshot" / "HEAD"
    assert head_path.is_file()
    assert head_path.read_text() == "ref: refs/heads/main\n"


def test_init_creates_refs_heads_directory(tmp_path):
    repository.init_repository(tmp_path)
    assert (tmp_path / ".snapshot" / "refs" / "heads").is_dir()


def test_init_does_not_create_main_branch_ref(tmp_path):
    repository.init_repository(tmp_path)
    assert not (tmp_path / ".snapshot" / "refs" / "heads" / "main").exists()


def test_init_is_idempotent_and_does_not_clobber_existing_head(tmp_path):
    repository.init_repository(tmp_path)
    head_path = tmp_path / ".snapshot" / "HEAD"
    head_path.write_text("ref: refs/heads/some-other-branch\n")

    repository.init_repository(tmp_path)  # re-run init

    assert head_path.read_text() == "ref: refs/heads/some-other-branch\n"