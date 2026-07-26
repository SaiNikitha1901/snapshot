"""Minimal CLI for manually exploring Snapshot's internals."""

import argparse
import sys
from pathlib import Path

from . import blob, index, objects, tree
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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()