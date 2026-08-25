"""The command envelope: one request in, one StudioResponse out, which
updates all five panels in a single round trip.
"""

from pydantic import BaseModel

from .animation import AnimationSequence
from .graph import CommitGraph
from .learn import LearnCardSet
from .objects import ObjectDetail
from .status import RepositoryStatus


class CommandRequest(BaseModel):
    input: str


class TerminalOutput(BaseModel):
    stdout_lines: list[str]
    stderr_lines: list[str]
    exit_code: int


class CommandMeta(BaseModel):
    raw_input: str
    name: str
    args: list[str]
    recognized: bool


class StudioResponse(BaseModel):
    terminal: TerminalOutput
    command: CommandMeta
    repository_status: RepositoryStatus
    commit_graph: CommitGraph
    animation: AnimationSequence | None = None
    focused_object: ObjectDetail | None = None
    learn: LearnCardSet | None = None
