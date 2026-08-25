"""The Object Graph DTO: the real object store, deduplicated by OID --
not a tree mirror. Two tree entries pointing at identical content are
the *same* node with two incoming edges; names live on edges (tree
entry names), never on nodes, matching tree.py's own model (a blob
never carries a filename). Layout coordinates (depth, lane) are
backend-owned, exactly like graph.py's generation/lane for the commit
graph -- the frontend only maps them to pixels.
"""

from typing import Literal

from pydantic import BaseModel


class ObjectGraphNode(BaseModel):
    oid: str
    short_oid: str
    kind: Literal["commit", "tree", "blob"]
    label: str
    depth: int
    lane: int
    is_head_commit: bool = False
    is_merge: bool | None = None


class ObjectGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class ObjectGraph(BaseModel):
    root_oid: str
    nodes: list[ObjectGraphNode]
    edges: list[ObjectGraphEdge]
