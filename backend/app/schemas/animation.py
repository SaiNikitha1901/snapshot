"""The Object Animation Pipeline's timeline: an ordered sequence of
internal-operation steps. The backend decides *what* happened (source
of truth for Git internals); the frontend only decides *how* to render
each step kind.
"""

from typing import Literal

from pydantic import BaseModel

AnimationStepKind = Literal[
    "init_repository",
    "hash_blob",
    "write_object",
    "update_index",
    "build_tree",
    "write_commit",
    "create_branch_ref",
    "update_ref",
    "move_head",
    "restore_working_directory",
    "find_merge_base",
    "diff_three_way",
    "conflict_marker",
    "fast_forward",
]


class AnimationStep(BaseModel):
    kind: AnimationStepKind
    label: str
    detail: str | None = None
    object_oid: str | None = None
    object_type: Literal["blob", "tree", "commit"] | None = None
    path: str | None = None
    ref_name: str | None = None


class AnimationSequence(BaseModel):
    command: str
    steps: list[AnimationStep]
