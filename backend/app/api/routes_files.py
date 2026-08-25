"""Backs the terminal's `edit <file>` overlay. Multi-line file content
doesn't fit as a single terminal input line, so it gets its own small
endpoint pair rather than being squeezed through CommandRequest.input.
A write still returns a full StudioResponse so status/graph update
exactly like any other command.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core import config
from app.schemas.command import CommandMeta, StudioResponse, TerminalOutput
from app.services import graph_builder, status_builder
from app.services.builtins import resolve_in_repo

router = APIRouter()


class FileReadResponse(BaseModel):
    path: str
    content: str
    exists: bool


class FileWriteRequest(BaseModel):
    path: str
    content: str


@router.get("/api/files/read", response_model=FileReadResponse)
def read_file(path: str) -> FileReadResponse:
    config.ensure_repo_root_exists()
    try:
        file_path = resolve_in_repo(config.REPO_ROOT, path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not file_path.is_file():
        return FileReadResponse(path=path, content="", exists=False)
    try:
        return FileReadResponse(path=path, content=file_path.read_text(), exists=True)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"'{path}' is binary and cannot be edited as text") from exc


@router.post("/api/files/write", response_model=StudioResponse)
def write_file(request: FileWriteRequest) -> StudioResponse:
    config.ensure_repo_root_exists()
    try:
        file_path = resolve_in_repo(config.REPO_ROOT, request.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(request.content)

    snapshot_dir = config.snapshot_dir()
    objects_dir = config.objects_dir()
    status = status_builder.build_status(snapshot_dir, objects_dir, config.index_path(), config.REPO_ROOT)
    graph = graph_builder.build_graph(snapshot_dir, objects_dir)

    return StudioResponse(
        terminal=TerminalOutput(
            stdout_lines=[f"wrote {len(request.content.encode())} bytes to {request.path}"],
            stderr_lines=[],
            exit_code=0,
        ),
        command=CommandMeta(raw_input=f"edit {request.path}", name="edit", args=[request.path], recognized=True),
        repository_status=status,
        commit_graph=graph,
    )
