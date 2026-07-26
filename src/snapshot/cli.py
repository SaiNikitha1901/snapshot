"""Minimal CLI for manually exploring Snapshot's internals."""

import argparse
import sys
from pathlib import Path

from . import blob, objects
from .repository import SNAPSHOT_DIR_NAME, init_repository


def find_objects_dir() -> Path:
    """Locate the object database for the repository in the current directory.

    Simplification: real Git walks up parent directories looking for
    .git. Snapshot only checks the current working directory for now.
    """
    objects_dir = Path.cwd() / SNAPSHOT_DIR_NAME / "objects"
    if not objects_dir.exists():
        print(
            "fatal: not a snapshot repository (.snapshot/objects not found "
            "in the current directory)",
            file=sys.stderr,
        )
        print("Run 'snapshot init' first.", file=sys.stderr)
        sys.exit(1)
    return objects_dir


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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()