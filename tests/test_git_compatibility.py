"""Snapshot's objects are byte-compatible with real Git.

Builds a history with Snapshot -- nested directories, an executable
file, a file/directory name-prefix collision, a branch, and a merge
commit -- then copies the raw object files into an empty Git repository
and asks real Git to verify them. Skipped when `git` isn't installed.
"""

import os
import shutil
import subprocess

import pytest

from snapshot import checkout, commit, index, merge, refs, repository, tree

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")


def _git(git_dir, *args):
    result = subprocess.run(
        ["git", f"--git-dir={git_dir}", *args], capture_output=True, text=True, check=True
    )
    return result.stdout


def _write(repo_root, path, content, executable=False):
    file_path = repo_root / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    if executable:
        os.chmod(file_path, 0o755)


def _commit_all(snapshot_dir, objects_dir, index_path, repo_root, message, timestamp):
    for file_path in index.collect_stageable_files(repo_root):
        index.stage_file(objects_dir, index_path, repo_root, file_path)
    tree_oid = tree.write_tree_from_index(objects_dir, index.read_index(index_path))
    new_commit = commit.build_commit(tree_oid, refs.resolve_head(snapshot_dir), message, timestamp=timestamp)
    commit_oid = commit.store_commit(objects_dir, new_commit)
    refs.update_head(snapshot_dir, commit_oid)
    return commit_oid


@pytest.fixture
def history(tmp_path):
    """A Snapshot repository whose main branch ends in a real merge commit."""
    repo_root = tmp_path / "work"
    repo_root.mkdir()
    snapshot_dir = repository.init_repository(repo_root)
    objects_dir, index_path = snapshot_dir / "objects", snapshot_dir / "index"

    _write(repo_root, "README.md", "hello\n")
    _write(repo_root, "run.sh", "#!/bin/sh\necho hi\n", executable=True)
    # "lib.txt" and the directory "lib" exercise Git's tree-entry ordering.
    _write(repo_root, "lib.txt", "notes\n")
    _write(repo_root, "lib/core.py", "x = 1\n")
    _commit_all(snapshot_dir, objects_dir, index_path, repo_root, "initial", 1700000000)

    refs.create_branch(snapshot_dir, "feature")
    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    _write(repo_root, "lib/extra.py", "y = 2\n")
    _commit_all(snapshot_dir, objects_dir, index_path, repo_root, "feature work", 1700000100)

    checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, "main")
    _write(repo_root, "README.md", "hello\nworld\n")
    _commit_all(snapshot_dir, objects_dir, index_path, repo_root, "main work", 1700000200)

    result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, "feature")
    assert result.kind == "merge_commit"
    return repo_root, objects_dir, result.commit_oid


@pytest.fixture
def git_dir(tmp_path, history):
    """An empty Git repository holding a copy of Snapshot's loose objects."""
    _, objects_dir, _ = history
    git_dir = tmp_path / "repo.git"
    subprocess.run(["git", "init", "--quiet", "--bare", str(git_dir)], check=True)
    shutil.copytree(objects_dir, git_dir / "objects", dirs_exist_ok=True)
    return git_dir


def test_git_fsck_accepts_every_snapshot_object(history, git_dir):
    _, _, merge_oid = history
    _git(git_dir, "update-ref", "refs/heads/main", merge_oid)

    # --strict turns Git's warnings (bad dates, unsorted trees, bad modes) into errors.
    _git(git_dir, "fsck", "--strict", "--no-dangling")


def test_git_reads_snapshot_merge_commit_and_history(history, git_dir):
    _, _, merge_oid = history

    parents = _git(git_dir, "rev-list", "--parents", "-n", "1", merge_oid).split()
    assert len(parents) == 3  # the merge commit itself + two parents

    messages = _git(git_dir, "log", "--format=%s", merge_oid).splitlines()
    assert sorted(messages) == sorted(["Merge feature into main", "main work", "feature work", "initial"])


def test_snapshot_tree_matches_git_write_tree(history, tmp_path):
    repo_root, objects_dir, merge_oid = history
    snapshot_tree = commit.read_commit(objects_dir, merge_oid).tree

    # Let real Git hash the same working directory from scratch.
    git_dir = tmp_path / "independent.git"
    subprocess.run(["git", "init", "--quiet", "--bare", str(git_dir)], check=True)
    for file_path in index.collect_stageable_files(repo_root):
        rel_path = file_path.relative_to(repo_root).as_posix()
        subprocess.run(
            ["git", f"--git-dir={git_dir}", f"--work-tree={repo_root}", "add", rel_path], check=True
        )
    git_tree = _git(git_dir, "write-tree").strip()

    assert snapshot_tree == git_tree
