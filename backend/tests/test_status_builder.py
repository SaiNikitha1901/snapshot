from app.services import command_dispatcher


def run(repo_root, text):
    return command_dispatcher.run_command(repo_root, text)


def test_status_before_init(repo_root):
    resp = run(repo_root, "ls")
    assert resp.repository_status.initialized is False
    assert resp.repository_status.working_directory_clean is True


def test_untracked_and_unstaged_and_clean_transitions(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo hi > tracked.txt")

    untracked_resp = run(repo_root, "ls")
    assert untracked_resp.repository_status.untracked_paths == ["tracked.txt"]
    assert untracked_resp.repository_status.working_directory_clean is False

    run(repo_root, "add tracked.txt")
    run(repo_root, 'commit -m "c1"')
    clean_resp = run(repo_root, "ls")
    assert clean_resp.repository_status.working_directory_clean is True
    assert clean_resp.repository_status.untracked_paths == []

    run(repo_root, "echo changed >> tracked.txt")
    dirty_resp = run(repo_root, "ls")
    assert dirty_resp.repository_status.unstaged_paths == ["tracked.txt"]
    assert dirty_resp.repository_status.working_directory_clean is False
