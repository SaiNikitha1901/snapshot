"""Builds the Object Graph: a breadth-first walk from any root object
(commit, tree, or blob) down through the real object store,
deduplicated by OID -- not a tree mirror. See schemas/object_graph.py
for why that distinction matters.

Read-only, same as graph_builder.py: only reads existing objects
through the engine's own `objects`/`tree`/`commit`/`refs` modules,
never creates anything.
"""

from collections import deque
from pathlib import Path

from snapshot import commit as commit_mod
from snapshot import objects as objects_mod
from snapshot import refs as refs_mod
from snapshot import tree as tree_mod

from app.schemas.object_graph import ObjectGraph, ObjectGraphEdge, ObjectGraphNode


def build_object_graph(snapshot_dir: Path, objects_dir: Path, root_oid: str) -> ObjectGraph:
    head_oid = _resolve_head_safely(snapshot_dir)

    nodes: dict[str, ObjectGraphNode] = {}
    edges: list[ObjectGraphEdge] = []
    depth: dict[str, int] = {root_oid: 0}
    lane_counters: dict[int, int] = {}
    queue: deque[str] = deque([root_oid])

    def link(source_oid: str, target_oid: str, label: str, source_depth: int) -> None:
        edges.append(
            ObjectGraphEdge(
                id=f"{source_oid}->{target_oid}:{label}", source=source_oid, target=target_oid, label=label
            )
        )
        # First discovery wins -- BFS guarantees that's the shortest depth
        # this object is reachable at, even if a later (deeper) path also
        # references it (e.g. a shared blob reachable from two trees).
        if target_oid not in depth:
            depth[target_oid] = source_depth + 1
            queue.append(target_oid)

    while queue:
        oid = queue.popleft()
        if oid in nodes:
            continue

        obj_type, content = objects_mod.read_object(objects_dir, oid)
        d = depth[oid]
        lane = lane_counters.get(d, 0)
        lane_counters[d] = lane + 1

        if obj_type == "commit":
            parsed = commit_mod.decode_commit(content)
            nodes[oid] = ObjectGraphNode(
                oid=oid,
                short_oid=oid[:7],
                kind="commit",
                label=(parsed.message.splitlines() or [""])[0] or "(empty message)",
                depth=d,
                lane=lane,
                is_head_commit=(oid == head_oid),
                is_merge=parsed.merge_parent is not None,
            )
            link(oid, parsed.tree, "tree", d)

        elif obj_type == "tree":
            entries = tree_mod.decode_tree_payload(content)
            entry_count = len(entries)
            nodes[oid] = ObjectGraphNode(
                oid=oid,
                short_oid=oid[:7],
                kind="tree",
                label=f"{entry_count} {'entry' if entry_count == 1 else 'entries'}",
                depth=d,
                lane=lane,
            )
            for entry in sorted(entries, key=lambda e: e.name):
                link(oid, entry.oid, entry.name, d)

        elif obj_type == "blob":
            nodes[oid] = ObjectGraphNode(
                oid=oid,
                short_oid=oid[:7],
                kind="blob",
                label=f"{len(content)} bytes",
                depth=d,
                lane=lane,
            )

        else:
            raise ValueError(f"unrecognized object type '{obj_type}' for {oid}")

    return ObjectGraph(root_oid=root_oid, nodes=list(nodes.values()), edges=edges)


def _resolve_head_safely(snapshot_dir: Path) -> str | None:
    try:
        return refs_mod.resolve_head(snapshot_dir)
    except ValueError:
        return None
