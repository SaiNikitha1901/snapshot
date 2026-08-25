"""Turns raw engine objects into the structured ObjectDetail DTOs the
Object Inspector renders. Read-only: never creates objects, only
reads them through the engine's existing `objects`, `tree`, `commit`,
and `refs` modules.
"""

from pathlib import Path

from snapshot import commit as commit_mod
from snapshot import objects as objects_mod
from snapshot import refs as refs_mod
from snapshot import tree as tree_mod

from app.schemas.objects import (
    BlobObject,
    BranchObject,
    CommitObject,
    HeadObject,
    ObjectDetail,
    TreeEntryRef,
    TreeObject,
)


def get_object_detail(objects_dir: Path, oid: str) -> ObjectDetail:
    """Look up any content-addressed object (blob, tree, or commit) by OID."""
    obj_type, content = objects_mod.read_object(objects_dir, oid)

    if obj_type == "blob":
        return _blob_detail(oid, content)
    if obj_type == "tree":
        return _tree_detail(oid, content)
    if obj_type == "commit":
        return _commit_detail(oid, content)
    raise ValueError(f"unrecognized object type '{obj_type}' for {oid}")


def _blob_detail(oid: str, content: bytes) -> BlobObject:
    try:
        text = content.decode()
        return BlobObject(oid=oid, size=len(content), content=text, is_binary=False)
    except UnicodeDecodeError:
        return BlobObject(oid=oid, size=len(content), content=None, is_binary=True)


def _tree_detail(oid: str, payload: bytes) -> TreeObject:
    entries = tree_mod.decode_tree_payload(payload)
    refs = [
        TreeEntryRef(mode=e.mode, name=e.name, oid=e.oid, type=tree_mod.entry_type(e.mode))
        for e in sorted(entries, key=lambda e: e.name)
    ]
    return TreeObject(oid=oid, entries=refs)


def _commit_detail(oid: str, payload: bytes) -> CommitObject:
    parsed = commit_mod.decode_commit(payload)
    return CommitObject(
        oid=oid,
        tree_oid=parsed.tree,
        parent_oid=parsed.parent,
        merge_parent_oid=parsed.merge_parent,
        author=parsed.author,
        committer=parsed.committer,
        message=parsed.message,
        is_merge=parsed.merge_parent is not None,
    )


def get_branch_detail(snapshot_dir: Path, branch_name: str) -> BranchObject:
    ref_path = snapshot_dir / "refs" / "heads" / branch_name
    commit_oid = refs_mod.read_branch_oid(ref_path)
    is_current = not refs_mod.is_detached(snapshot_dir) and refs_mod.current_branch_name(snapshot_dir) == branch_name
    return BranchObject(name=branch_name, commit_oid=commit_oid, is_current=is_current)


def get_head_detail(snapshot_dir: Path) -> HeadObject:
    detached = refs_mod.is_detached(snapshot_dir)
    commit_oid = refs_mod.resolve_head(snapshot_dir)
    branch_name = None if detached else refs_mod.current_branch_name(snapshot_dir)
    return HeadObject(detached=detached, branch_name=branch_name, commit_oid=commit_oid)
