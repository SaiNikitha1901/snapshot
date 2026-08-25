from app.services import command_dispatcher


def run(repo_root, text):
    return command_dispatcher.run_command(repo_root, text)


def test_unknown_command_before_init(repo_root):
    resp = run(repo_root, "frobnicate")
    assert resp.command.recognized is False
    assert resp.terminal.exit_code == 127
    assert "command not found" in resp.terminal.stderr_lines[0]
    assert resp.repository_status.initialized is False


def test_git_command_before_init_is_rejected(repo_root):
    resp = run(repo_root, "add .")
    assert resp.terminal.exit_code == 1
    assert "not a snapshot repository" in resp.terminal.stderr_lines[0]


def test_init_produces_animation_and_learn_card_once(repo_root):
    resp = run(repo_root, "init")
    assert resp.repository_status.initialized is True
    assert resp.animation is not None
    assert resp.animation.command == "init"
    assert resp.learn is not None
    assert resp.learn.cards[0].trigger == "repository_initialized"

    resp2 = run(repo_root, "init")
    assert resp2.animation is None
    assert resp2.learn is None


def test_echo_and_add_and_first_commit(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo hello > greeting.txt")

    add_resp = run(repo_root, "add greeting.txt")
    assert add_resp.terminal.stdout_lines == ["staged greeting.txt"]
    assert add_resp.animation is not None
    assert add_resp.repository_status.staged_paths == ["greeting.txt"]
    assert add_resp.focused_object.kind == "blob"
    assert add_resp.focused_object.content == "hello\n"

    commit_resp = run(repo_root, 'commit -m "first commit"')
    assert commit_resp.terminal.exit_code == 0
    commit_oid = commit_resp.terminal.stdout_lines[0]
    assert len(commit_oid) == 40
    assert commit_resp.focused_object.kind == "commit"
    assert commit_resp.focused_object.parent_oid is None
    assert commit_resp.learn.cards[0].trigger == "first_commit"
    assert commit_resp.repository_status.current_commit_oid == commit_oid
    assert commit_resp.repository_status.staged_paths == []

    second_commit = run(repo_root, 'commit -m "no changes"')
    # The engine only refuses a commit when the index is empty (see
    # tree.write_tree_from_index) -- it doesn't check "unchanged since
    # HEAD" the way real Git's "nothing to commit" does. A non-empty
    # index re-commits successfully even with an identical tree.
    assert second_commit.terminal.exit_code == 0
    assert second_commit.focused_object.tree_oid == commit_resp.focused_object.tree_oid
    assert second_commit.focused_object.parent_oid == commit_oid


def test_branch_and_checkout_and_detached_head(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo hi > a.txt")
    run(repo_root, "add a.txt")
    commit_resp = run(repo_root, 'commit -m "base"')
    base_oid = commit_resp.terminal.stdout_lines[0]

    branch_resp = run(repo_root, "branch feature")
    assert branch_resp.terminal.stdout_lines == ["Created branch 'feature'"]
    assert branch_resp.learn.cards[0].trigger == "branch_created"

    checkout_resp = run(repo_root, "checkout feature")
    assert checkout_resp.repository_status.current_branch == "feature"
    assert checkout_resp.repository_status.head_detached is False
    assert checkout_resp.learn.cards[0].trigger == "checkout_branch"

    detached_resp = run(repo_root, f"checkout {base_oid}")
    assert detached_resp.repository_status.head_detached is True
    assert detached_resp.repository_status.current_branch is None
    assert detached_resp.learn.cards[0].trigger == "detached_head"


def test_reflog_command_empty_then_populated(repo_root):
    run(repo_root, "init")
    empty_resp = run(repo_root, "reflog")
    assert empty_resp.terminal.stdout_lines == ["(reflog is empty)"]
    assert empty_resp.learn is None  # no HEAD movement happened, nothing to view yet

    run(repo_root, "echo hi > a.txt")
    run(repo_root, "add a.txt")
    commit_resp = run(repo_root, 'commit -m "first"')
    commit_oid = commit_resp.terminal.stdout_lines[0]

    reflog_resp = run(repo_root, "reflog")
    assert reflog_resp.terminal.exit_code == 0
    assert reflog_resp.terminal.stdout_lines == [f"{commit_oid[:7]} HEAD@{{0}}: commit (initial): first"]
    assert reflog_resp.learn.cards[0].trigger == "reflog_viewed"


def test_checkout_away_from_orphaned_detached_commit_shows_orphaned_commit_card(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo a > f.txt")
    run(repo_root, "add f.txt")
    first_oid = run(repo_root, 'commit -m "c1"').terminal.stdout_lines[0]

    run(repo_root, "echo b >> f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "c2"')

    run(repo_root, f"checkout {first_oid}")
    run(repo_root, "echo c >> f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "orphaned"')

    move_away = run(repo_root, "checkout main")
    assert move_away.learn.cards[0].trigger == "orphaned_commit"


def test_checkout_away_from_detached_but_still_reachable_commit_shows_normal_card(repo_root):
    # Detaching at a commit that a branch still points at (e.g. the branch
    # tip itself) and then moving away should NOT trigger the orphaned-commit
    # card -- nothing became unreachable.
    run(repo_root, "init")
    run(repo_root, "echo a > f.txt")
    run(repo_root, "add f.txt")
    tip_oid = run(repo_root, 'commit -m "c1"').terminal.stdout_lines[0]

    run(repo_root, f"checkout {tip_oid}")
    move_away = run(repo_root, "checkout main")
    assert move_away.learn.cards[0].trigger == "checkout_branch"


def test_merge_fast_forward(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo one > f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "c1"')
    run(repo_root, "branch feature")
    run(repo_root, "checkout feature")
    run(repo_root, "echo two >> f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "c2 on feature"')
    run(repo_root, "checkout main")

    merge_resp = run(repo_root, "merge feature")
    assert "Fast-forward" in merge_resp.terminal.stdout_lines[0]
    assert merge_resp.learn.cards[0].trigger == "merge_fast_forward"
    assert merge_resp.animation.steps[-1].kind == "restore_working_directory"


def test_merge_three_way_produces_merge_commit(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo base > shared.txt")
    run(repo_root, "add shared.txt")
    run(repo_root, 'commit -m "base"')
    run(repo_root, "branch feature")

    run(repo_root, "echo main-line >> shared.txt")
    run(repo_root, "add shared.txt")
    run(repo_root, 'commit -m "main change"')

    run(repo_root, "checkout feature")
    run(repo_root, "echo other.txt content > other.txt")
    run(repo_root, "add other.txt")
    run(repo_root, 'commit -m "feature change"')

    run(repo_root, "checkout main")
    merge_resp = run(repo_root, "merge feature")

    assert "Merge commit created" in merge_resp.terminal.stdout_lines[0]
    assert merge_resp.focused_object.kind == "commit"
    assert merge_resp.focused_object.is_merge is True
    assert merge_resp.learn.cards[0].trigger == "merge_commit"

    graph = merge_resp.commit_graph
    merge_node = next(c for c in graph.commits if c.oid == merge_resp.focused_object.oid)
    assert merge_node.is_merge is True
    assert merge_node.merge_parent_oid is not None


def test_merge_conflict_reports_paths_and_no_learn_crash(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo base > f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "base"')
    run(repo_root, "branch feature")

    run(repo_root, "echo main-version > f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "main edits f"')

    run(repo_root, "checkout feature")
    run(repo_root, "echo feature-version > f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "feature edits f"')

    run(repo_root, "checkout main")
    conflict_resp = run(repo_root, "merge feature")

    assert conflict_resp.terminal.exit_code == 1
    assert any("f.txt" in line for line in conflict_resp.terminal.stderr_lines)
    assert conflict_resp.learn.cards[0].trigger == "merge_conflict"
    assert "f.txt" in conflict_resp.repository_status.conflicted_paths


def test_builtins_are_sandboxed_to_repo_root(repo_root):
    run(repo_root, "init")
    escape_resp = run(repo_root, "cat ../../etc/passwd")
    assert escape_resp.terminal.exit_code == 1
    assert "outside the repository" in escape_resp.terminal.stderr_lines[0]


def test_ls_and_mkdir_and_rm(repo_root):
    run(repo_root, "init")
    run(repo_root, "mkdir sub")
    run(repo_root, "touch sub/file.txt")
    ls_resp = run(repo_root, "ls sub")
    assert ls_resp.terminal.stdout_lines == ["file.txt"]

    rm_resp = run(repo_root, "rm sub/file.txt")
    assert rm_resp.terminal.exit_code == 0
    ls_resp_2 = run(repo_root, "ls sub")
    assert ls_resp_2.terminal.stdout_lines == []
