"""The Commit Graph DTO: everything the Visualization panel's permanent
React Flow graph needs, including backend-computed layout coordinates
(`generation`, `lane`) so the frontend never invents positioning --
it only maps (generation, lane) to pixels.
"""

from pydantic import BaseModel


class GraphCommitNode(BaseModel):
    oid: str
    short_oid: str
    message_summary: str
    author: str
    parent_oid: str | None
    merge_parent_oid: str | None
    is_merge: bool
    generation: int
    lane: int
    is_head_commit: bool


class GraphBranchRef(BaseModel):
    name: str
    commit_oid: str | None
    is_current: bool
    lane: int


class CommitGraph(BaseModel):
    commits: list[GraphCommitNode]
    branches: list[GraphBranchRef]
    head_detached: bool
    head_commit_oid: str | None
