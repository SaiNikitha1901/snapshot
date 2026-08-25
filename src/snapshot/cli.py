"""Minimal CLI for manually exploring Snapshot's internals."""

import argparse
import sys
from pathlib import Path

from . import blob, checkout, commit, index, merge, objects, reflog, refs, tree
from .repository import SNAPSHOT_DIR_NAME, init_repository


def find_snapshot_dir() -> Path:
    """Return the .snapshot directory for the repo in the current directory.

    Only checks that the repository exists (via .snapshot/objects) --
    not that any specific file inside it (like the index) exists yet.

    Simplification: real Git walks up parent directories looking for
    .git. Snapshot only checks the current working directory for now.
    """
    snapshot_dir = Path.cwd() / SNAPSHOT_DIR_NAME
    if not (snapshot_dir / "objects").exists():
        print(
            "fatal: not a snapshot repository (.snapshot/objects not found "
            "in the current directory)",
            file=sys.stderr,
        )
        print("Run 'snapshot init' first.", file=sys.stderr)
        sys.exit(1)
    return snapshot_dir


def find_objects_dir() -> Path:
    """Locate the object database for the repository in the current directory."""
    return find_snapshot_dir() / "objects"


def find_index_path() -> Path:
    """Locate the index file path for the repository (may not exist yet)."""
    return find_snapshot_dir() / "index"


def cmd_init(args: argparse.Namespace) -> None:
    snapshot_dir = init_repository(Path.cwd())
    print(f"Initialized empty Snapshot repository in {snapshot_dir}")


def cmd_hash_object(args: argparse.Namespace) -> None:
    file_path = Path(args.file)
    if not file_path.is_file():
        print(f"fatal: '{file_path}' is not a file", file=sys.stderr)
        sys.exit(1)

    if args.write:
        objects_dir = find_objects_dir()
        oid = blob.store_blob(objects_dir, file_path)
    else:
        oid = blob.compute_blob_oid(file_path)

    print(oid)


def cmd_cat_file(args: argparse.Namespace) -> None:
    objects_dir = find_objects_dir()
    try:
        obj_type, content = objects.read_object(objects_dir, args.oid)
    except FileNotFoundError:
        print(f"fatal: object {args.oid} not found", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"type: {obj_type}")
    print(f"size: {len(content)} bytes")
    print("content:")

    if obj_type == "commit":
        try:
            parsed_commit = commit.decode_commit(content)
        except ValueError as exc:
            print(f"<malformed commit: {exc}>")
            return
        print(f"tree {parsed_commit.tree}")
        if parsed_commit.parent is not None:
            print(f"parent {parsed_commit.parent}")
        if parsed_commit.merge_parent is not None:
            print(f"parent {parsed_commit.merge_parent}")
        print(f"author {parsed_commit.author}")
        print(f"committer {parsed_commit.committer}")
        print()
        print(parsed_commit.message)
        return

    try:
        print(content.decode())
    except UnicodeDecodeError:
        print(f"<binary content, {len(content)} bytes>")


def cmd_add(args: argparse.Namespace) -> None:
    objects_dir = find_objects_dir()
    index_path = find_index_path()
    repo_root = Path.cwd()

    if args.path == ".":
        targets = index.collect_stageable_files(repo_root)
        if not targets:
            print("nothing to stage")
            return
    else:
        target = Path(args.path)
        if target.is_dir():
            print(
                f"fatal: '{target}' is a directory; use 'snapshot add .' "
                "to stage all files",
                file=sys.stderr,
            )
            sys.exit(1)
        if not target.is_file():
            print(f"fatal: '{target}' is not a file", file=sys.stderr)
            sys.exit(1)
        targets = [target]

    for file_path in targets:
        try:
            entry = index.stage_file(objects_dir, index_path, repo_root, file_path)
        except ValueError as exc:
            print(f"fatal: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"staged {entry.path}")


def cmd_show_index(args: argparse.Namespace) -> None:
    index_path = find_index_path()
    entries = index.read_index(index_path)

    if not entries:
        print("(index is empty)")
        return

    for entry in entries:
        print(f"{entry.mode}  {entry.oid}  {entry.path}")


def cmd_write_tree(args: argparse.Namespace) -> None:
    objects_dir = find_objects_dir()
    index_path = find_index_path()
    entries = index.read_index(index_path)

    try:
        root_oid = tree.write_tree_from_index(objects_dir, entries)
    except ValueError as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        sys.exit(1)

    print(root_oid)


def cmd_ls_tree(args: argparse.Namespace) -> None:
    objects_dir = find_objects_dir()
    try:
        obj_type, payload = objects.read_object(objects_dir, args.oid)
    except FileNotFoundError:
        print(f"fatal: object {args.oid} not found", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        sys.exit(1)

    if obj_type != "tree":
        print(f"fatal: object {args.oid} is a {obj_type}, not a tree", file=sys.stderr)
        sys.exit(1)

    entries = tree.decode_tree_payload(payload)
    for entry in sorted(entries, key=lambda e: e.name):
        display_mode = entry.mode.zfill(6)
        print(f"{display_mode} {tree.entry_type(entry.mode)} {entry.oid} {entry.name}")


def cmd_commit(args: argparse.Namespace) -> None:
    snapshot_dir = find_snapshot_dir()
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"

    entries = index.read_index(index_path)
    if not entries:
        print(
            "fatal: nothing to commit (index is empty); "
            "use 'snapshot add' to stage changes first",
            file=sys.stderr,
        )
        sys.exit(1)

    tree_oid = tree.write_tree_from_index(objects_dir, entries)

    try:
        parent_oid = refs.resolve_head(snapshot_dir)
    except ValueError as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        sys.exit(1)

    new_commit = commit.build_commit(tree_oid, parent_oid, args.message)
    commit_oid = commit.store_commit(objects_dir, new_commit)

    detached = refs.is_detached(snapshot_dir)
    reflog_prefix = "commit (initial)" if parent_oid is None else "commit"
    refs.update_head(snapshot_dir, commit_oid, reflog_message=f"{reflog_prefix}: {args.message}")

    print(commit_oid)
    if detached:
        print("Note: you are in 'detached HEAD' state; no branch was moved by this commit.")


def cmd_log(args: argparse.Namespace) -> None:
    snapshot_dir = find_snapshot_dir()
    objects_dir = snapshot_dir / "objects"

    try:
        current_oid = refs.resolve_head(snapshot_dir)
    except ValueError as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        sys.exit(1)

    if current_oid is None:
        print("fatal: no commits yet", file=sys.stderr)
        sys.exit(1)

    while current_oid is not None:
        try:
            current_commit = commit.read_commit(objects_dir, current_oid)
        except (FileNotFoundError, ValueError) as exc:
            print(f"fatal: {exc}", file=sys.stderr)
            sys.exit(1)

        print(f"commit {current_oid}")
        print(f"Author: {current_commit.author}")
        print()
        for line in current_commit.message.splitlines() or [""]:
            print(f"    {line}")
        print()

        current_oid = current_commit.parent


def cmd_reflog(args: argparse.Namespace) -> None:
    snapshot_dir = find_snapshot_dir()
    entries = list(reversed(reflog.read_entries(snapshot_dir)))

    if not entries:
        print("(reflog is empty)")
        return

    for i, entry in enumerate(entries):
        print(f"{entry.new_oid[:7]} HEAD@{{{i}}}: {entry.message}")


def cmd_rev_parse(args: argparse.Namespace) -> None:
    if args.ref != "HEAD":
        print(f"fatal: only 'HEAD' is supported, got '{args.ref}'", file=sys.stderr)
        sys.exit(1)

    snapshot_dir = find_snapshot_dir()

    try:
        oid = refs.resolve_head(snapshot_dir)
    except ValueError as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        sys.exit(1)

    if oid is None:
        print("fatal: HEAD does not point to any commit yet (no commits made)", file=sys.stderr)
        sys.exit(1)

    print(oid)


def cmd_branch(args: argparse.Namespace) -> None:
    snapshot_dir = find_snapshot_dir()

    if args.name is None:
        _print_branch_list(snapshot_dir)
        return

    try:
        refs.create_branch(snapshot_dir, args.name)
    except ValueError as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Created branch '{args.name}'")


def _print_branch_list(snapshot_dir: Path) -> None:
    branch_names = refs.list_branches(snapshot_dir)
    detached = refs.is_detached(snapshot_dir)
    current_branch = None if detached else refs.current_branch_name(snapshot_dir)

    if detached:
        print(f"* (HEAD detached at {refs.resolve_head(snapshot_dir)})")

    if not branch_names:
        if not detached:
            print("(no branches yet)")
        return

    for name in branch_names:
        marker = "*" if name == current_branch else " "
        print(f"{marker} {name}")


def cmd_checkout(args: argparse.Namespace) -> None:
    snapshot_dir = find_snapshot_dir()
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = Path.cwd()

    target = args.target

    try:
        if refs.branch_exists(snapshot_dir, target):
            checkout.checkout_branch(snapshot_dir, objects_dir, index_path, repo_root, target)
            print(f"Switched to branch '{target}'")
        else:
            commit_oid = checkout.checkout_commit(
                snapshot_dir, objects_dir, index_path, repo_root, target
            )
            print(f"Note: checking out '{target}'.")
            print(f"HEAD is now detached at {commit_oid}")
    except ValueError as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_merge(args: argparse.Namespace) -> None:
    snapshot_dir = find_snapshot_dir()
    objects_dir = snapshot_dir / "objects"
    index_path = snapshot_dir / "index"
    repo_root = Path.cwd()

    try:
        result = merge.merge_branch(snapshot_dir, objects_dir, index_path, repo_root, args.branch)
    except ValueError as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        sys.exit(1)

    if result.kind == "already_up_to_date":
        print("Already up to date.")
    elif result.kind == "fast_forward":
        print(f"Fast-forward merge: branch now at {result.commit_oid}")
    elif result.kind == "merge_commit":
        print(f"Merge commit created: {result.commit_oid}")
    elif result.kind == "conflict":
        print("Auto-merging failed with conflicts in:", file=sys.stderr)
        for path in result.conflicted_paths:
            print(f"  both modified: {path}", file=sys.stderr)
        print(file=sys.stderr)
        print(
            "Snapshot (like Git) will not guess how to combine these "
            "overlapping edits. Conflict markers have been written into "
            "the file(s) above -- edit them by hand to keep what you "
            "want, remove the <<<<<<<, =======, and >>>>>>> marker "
            "lines, then 'snapshot add' and 'snapshot commit' to finish.",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="snapshot", description="Educational Git internals explorer"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a new Snapshot repository")
    init_parser.set_defaults(func=cmd_init)

    hash_parser = subparsers.add_parser(
        "hash-object", help="Compute (and optionally store) the blob OID for a file"
    )
    hash_parser.add_argument("file", help="Path to the file to hash")
    hash_parser.add_argument(
        "-w", "--write", action="store_true",
        help="Also write the object to the object database (default: compute only)",
    )
    hash_parser.set_defaults(func=cmd_hash_object)

    cat_parser = subparsers.add_parser("cat-file", help="Inspect a stored object by OID")
    cat_parser.add_argument("oid", help="The object ID to look up")
    cat_parser.set_defaults(func=cmd_cat_file)

    add_parser = subparsers.add_parser(
        "add", help="Stage a file (or '.' for all project files)"
    )
    add_parser.add_argument("path", help="File to stage, or '.' to stage all project files")
    add_parser.set_defaults(func=cmd_add)

    show_index_parser = subparsers.add_parser("show-index", help="Show staged entries")
    show_index_parser.set_defaults(func=cmd_show_index)

    write_tree_parser = subparsers.add_parser(
        "write-tree", help="Build tree objects from the index and print the root tree OID"
    )
    write_tree_parser.set_defaults(func=cmd_write_tree)

    ls_tree_parser = subparsers.add_parser("ls-tree", help="List the entries of a tree object")
    ls_tree_parser.add_argument("oid", help="The tree object's OID")
    ls_tree_parser.set_defaults(func=cmd_ls_tree)

    commit_parser = subparsers.add_parser(
        "commit", help="Create a commit from the currently staged index"
    )
    commit_parser.add_argument("-m", "--message", required=True, help="Commit message")
    commit_parser.set_defaults(func=cmd_commit)

    log_parser = subparsers.add_parser("log", help="Show commit history starting from HEAD")
    log_parser.set_defaults(func=cmd_log)

    reflog_parser = subparsers.add_parser(
        "reflog", help="Show every commit HEAD has pointed at, newest first"
    )
    reflog_parser.set_defaults(func=cmd_reflog)

    rev_parse_parser = subparsers.add_parser(
        "rev-parse", help="Resolve a ref to a commit OID"
    )
    rev_parse_parser.add_argument("ref", help="Only 'HEAD' is currently supported")
    rev_parse_parser.set_defaults(func=cmd_rev_parse)

    branch_parser = subparsers.add_parser(
        "branch", help="List branches, or create a new one pointing at HEAD"
    )
    branch_parser.add_argument(
        "name", nargs="?", help="Name of the new branch to create; omit to list branches"
    )
    branch_parser.set_defaults(func=cmd_branch)

    checkout_parser = subparsers.add_parser(
        "checkout", help="Switch to a branch, or detach HEAD onto a specific commit"
    )
    checkout_parser.add_argument("target", help="Branch name or commit OID to check out")
    checkout_parser.set_defaults(func=cmd_checkout)

    merge_parser = subparsers.add_parser(
        "merge", help="Merge a branch into the current branch"
    )
    merge_parser.add_argument("branch", help="Name of the branch to merge into the current branch")
    merge_parser.set_defaults(func=cmd_merge)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()