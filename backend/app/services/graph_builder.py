"""Builds the Commit Graph DTO: walks every branch tip (and a detached
HEAD, if any) back through parent links, and computes backend-owned
layout coordinates so the frontend never invents graph positioning --
only maps (generation, lane) to pixels.

Layout algorithm (intentionally simple -- these are small educational
graphs, no octopus merges):
  - generation: longest-path distance from a root commit (no parents).
    Root commits are generation 0; a commit's generation is always
    strictly greater than both of its parents', so merge commits
    always render after both sides they combine.
  - lane: each branch claims a lane, "main" first (if present) then
    alphabetically. Starting from each branch's tip and processing
    branches in that lane order, every not-yet-claimed ancestor is
    assigned that branch's lane -- so shared history is claimed by
    whichever branch reaches it first (main, if it exists), and a
    feature branch's lane is only visible on the commits unique to it.
"""

from pathlib import Path

from snapshot import commit as commit_mod
from snapshot import refs as refs_mod
from snapshot.commit import Commit

from app.schemas.graph import CommitGraph, GraphBranchRef, GraphCommitNode


def build_graph(snapshot_dir: Path, objects_dir: Path) -> CommitGraph:
    if not (snapshot_dir / "HEAD").exists():
        return CommitGraph(commits=[], branches=[], head_detached=False, head_commit_oid=None)

    branch_names = refs_mod.list_branches(snapshot_dir)
    head_detached = refs_mod.is_detached(snapshot_dir)
    head_commit_oid = refs_mod.resolve_head(snapshot_dir) if _repo_has_commits(snapshot_dir) else None
    current_branch = None if head_detached else _current_branch_or_none(snapshot_dir)

    branch_tips = {name: refs_mod.read_branch_oid(snapshot_dir / "refs" / "heads" / name) for name in branch_names}

    commits_by_oid = _collect_reachable_commits(
        objects_dir,
        list(branch_tips.values()) + ([head_commit_oid] if head_detached else []),
    )

    generation = _compute_generations(commits_by_oid)
    ordered_branch_names = sorted(branch_names, key=lambda n: (n != "main", n))
    branch_lane = {name: i for i, name in enumerate(ordered_branch_names)}
    commit_lane = _assign_lanes(commits_by_oid, branch_tips, ordered_branch_names, branch_lane)

    if head_detached and head_commit_oid and head_commit_oid not in commit_lane:
        _claim_ancestry(commits_by_oid, commit_lane, head_commit_oid, len(ordered_branch_names))

    nodes = [
        GraphCommitNode(
            oid=oid,
            short_oid=oid[:7],
            message_summary=(c.message.splitlines() or [""])[0],
            author=c.author,
            parent_oid=c.parent,
            merge_parent_oid=c.merge_parent,
            is_merge=c.merge_parent is not None,
            generation=generation[oid],
            lane=commit_lane.get(oid, 0),
            is_head_commit=(oid == head_commit_oid),
        )
        for oid, c in commits_by_oid.items()
    ]
    nodes.sort(key=lambda n: (n.generation, n.lane))

    branches = [
        GraphBranchRef(
            name=name,
            commit_oid=branch_tips.get(name),
            is_current=(not head_detached and name == current_branch),
            lane=branch_lane[name],
        )
        for name in branch_names
    ]

    return CommitGraph(
        commits=nodes, branches=branches, head_detached=head_detached, head_commit_oid=head_commit_oid
    )


def _repo_has_commits(snapshot_dir: Path) -> bool:
    try:
        refs_mod.resolve_head(snapshot_dir)
        return True
    except ValueError:
        return False


def _current_branch_or_none(snapshot_dir: Path) -> str | None:
    try:
        return refs_mod.current_branch_name(snapshot_dir)
    except ValueError:
        return None


def _collect_reachable_commits(objects_dir: Path, seed_oids: list[str | None]) -> dict[str, Commit]:
    commits_by_oid: dict[str, Commit] = {}
    stack = [oid for oid in seed_oids if oid]
    while stack:
        oid = stack.pop()
        if oid in commits_by_oid:
            continue
        c = commit_mod.read_commit(objects_dir, oid)
        commits_by_oid[oid] = c
        if c.parent:
            stack.append(c.parent)
        if c.merge_parent:
            stack.append(c.merge_parent)
    return commits_by_oid


def _compute_generations(commits_by_oid: dict[str, Commit]) -> dict[str, int]:
    generation: dict[str, int] = {}

    def gen(oid: str) -> int:
        if oid in generation:
            return generation[oid]
        c = commits_by_oid[oid]
        parents = [p for p in (c.parent, c.merge_parent) if p]
        generation[oid] = 0 if not parents else 1 + max(gen(p) for p in parents)
        return generation[oid]

    for oid in commits_by_oid:
        gen(oid)
    return generation


def _claim_ancestry(commits_by_oid: dict[str, Commit], commit_lane: dict[str, int], start_oid: str, lane: int) -> None:
    stack = [start_oid]
    while stack:
        oid = stack.pop()
        if oid in commit_lane:
            continue
        commit_lane[oid] = lane
        c = commits_by_oid[oid]
        if c.parent:
            stack.append(c.parent)
        if c.merge_parent:
            stack.append(c.merge_parent)


def _assign_lanes(
    commits_by_oid: dict[str, Commit],
    branch_tips: dict[str, str | None],
    ordered_branch_names: list[str],
    branch_lane: dict[str, int],
) -> dict[str, int]:
    commit_lane: dict[str, int] = {}
    for name in ordered_branch_names:
        tip = branch_tips.get(name)
        if tip:
            _claim_ancestry(commits_by_oid, commit_lane, tip, branch_lane[name])
    return commit_lane
