from app.core import config
from app.services import command_dispatcher, reflog_service


def run(repo_root, text):
    return command_dispatcher.run_command(repo_root, text)


def test_empty_reflog_before_any_head_movement(repo_root):
    run(repo_root, "init")
    reflog = reflog_service.build_reflog(config.snapshot_dir(), config.objects_dir())
    assert reflog.entries == []


def test_reflog_records_commit_checkout_and_detach_newest_first(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo a > f.txt")
    run(repo_root, "add f.txt")
    commit_resp = run(repo_root, 'commit -m "c1"')
    base_oid = commit_resp.terminal.stdout_lines[0]

    run(repo_root, "branch feature")
    checkout_resp = run(repo_root, "checkout feature")
    assert checkout_resp.terminal.exit_code == 0

    reflog = reflog_service.build_reflog(config.snapshot_dir(), config.objects_dir())
    messages = [e.message for e in reflog.entries]
    assert messages[0].startswith("checkout: moving from")  # entries are newest-first
    assert messages[1].startswith("commit (initial):")
    assert reflog.entries[1].new_oid == base_oid
    assert reflog.entries[-1].old_oid is None  # the very first entry ever recorded, oldest last


def test_demo_scenario_orphaned_commit_marked_unreachable_in_reflog(repo_root):
    # The exact educational flow from the feature request: create commit ->
    # detach HEAD -> create commit -> move away -> the detached commit is
    # unreachable from the commit graph, but still fully visible (and
    # recoverable by oid) via the reflog.
    run(repo_root, "init")
    run(repo_root, "echo a > f.txt")
    run(repo_root, "add f.txt")
    first = run(repo_root, 'commit -m "c1"')
    first_oid = first.terminal.stdout_lines[0]

    run(repo_root, "echo b >> f.txt")
    run(repo_root, "add f.txt")
    second = run(repo_root, 'commit -m "c2"')
    second_oid = second.terminal.stdout_lines[0]

    detach_resp = run(repo_root, f"checkout {first_oid}")
    assert detach_resp.repository_status.head_detached is True

    run(repo_root, "echo c >> f.txt")
    run(repo_root, "add f.txt")
    orphan = run(repo_root, 'commit -m "orphaned"')
    orphan_oid = orphan.terminal.stdout_lines[0]

    move_away = run(repo_root, "checkout main")
    assert move_away.repository_status.current_branch == "main"

    reflog = reflog_service.build_reflog(config.snapshot_dir(), config.objects_dir())
    by_oid = {e.new_oid: e for e in reflog.entries}

    assert by_oid[orphan_oid].is_reachable is False
    assert by_oid[first_oid].is_reachable is True
    assert by_oid[second_oid].is_reachable is True

    # the checkout back to main should have recorded a matching learn card
    # via the "orphaned_commit" trigger on the dispatcher, checked separately
    # in test_command_dispatcher.py -- here we only verify the reflog's own
    # reachability signal, which is the data that view is built from.
