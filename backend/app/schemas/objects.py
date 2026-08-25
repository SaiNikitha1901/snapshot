"""Structured representations of the five object kinds the Object
Inspector can display: Blob, Tree, Commit, Branch, HEAD.

A discriminated union (`kind`) lets `focused_object` on StudioResponse,
and the GET /api/objects/{oid} response, carry any one of them with a
type-safe frontend switch on `kind`.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class TreeEntryRef(BaseModel):
    mode: str
    name: str
    oid: str
    type: Literal["blob", "tree"]


class BlobObject(BaseModel):
    kind: Literal["blob"] = "blob"
    oid: str
    size: int
    content: str | None = None
    is_binary: bool = False


class TreeObject(BaseModel):
    kind: Literal["tree"] = "tree"
    oid: str
    entries: list[TreeEntryRef]


class CommitObject(BaseModel):
    kind: Literal["commit"] = "commit"
    oid: str
    tree_oid: str
    parent_oid: str | None
    merge_parent_oid: str | None
    author: str
    committer: str
    message: str
    is_merge: bool


class BranchObject(BaseModel):
    kind: Literal["branch"] = "branch"
    name: str
    commit_oid: str | None
    is_current: bool


class HeadObject(BaseModel):
    kind: Literal["head"] = "head"
    detached: bool
    branch_name: str | None
    commit_oid: str | None


ObjectDetail = Annotated[
    BlobObject | TreeObject | CommitObject | BranchObject | HeadObject,
    Field(discriminator="kind"),
]
