"""No test_cli.py existed before this feature -- scoped narrowly to the
new `reflog` command rather than retroactively covering all of cli.py.
"""

import argparse

from snapshot import cli, commit, index, refs, tree
from snapshot.repository import init_repository


def _init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_repository(tmp_path)


def _commit_via_cli(tmp_path, message: str) -> str:
    entries = index.read_index(tmp_path / ".snapshot" / "index")
    tree_oid = tree.write_tree_from_index(tmp_path / ".snapshot" / "objects", entries)
    parent_oid = refs.resolve_head(tmp_path / ".snapshot")
    new_commit = commit.build_commit(tree_oid, parent_oid, message)
    commit_oid = commit.store_commit(tmp_path / ".snapshot" / "objects", new_commit)
    prefix = "commit (initial)" if parent_oid is None else "commit"
    refs.update_head(tmp_path / ".snapshot", commit_oid, reflog_message=f"{prefix}: {message}")
    return commit_oid


def test_reflog_empty_before_any_commits(tmp_path, monkeypatch, capsys):
    _init(tmp_path, monkeypatch)

    cli.cmd_reflog(argparse.Namespace())

    assert capsys.readouterr().out.strip() == "(reflog is empty)"


def test_reflog_lists_entries_newest_first(tmp_path, monkeypatch, capsys):
    _init(tmp_path, monkeypatch)
    (tmp_path / "a.txt").write_text("hello\n")
    index.stage_file(tmp_path / ".snapshot" / "objects", tmp_path / ".snapshot" / "index", tmp_path, tmp_path / "a.txt")
    first_oid = _commit_via_cli(tmp_path, "first commit")

    (tmp_path / "a.txt").write_text("hello again\n")
    index.stage_file(tmp_path / ".snapshot" / "objects", tmp_path / ".snapshot" / "index", tmp_path, tmp_path / "a.txt")
    second_oid = _commit_via_cli(tmp_path, "second commit")

    cli.cmd_reflog(argparse.Namespace())

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    assert lines[0] == f"{second_oid[:7]} HEAD@{{0}}: commit: second commit"
    assert lines[1] == f"{first_oid[:7]} HEAD@{{1}}: commit (initial): first commit"
