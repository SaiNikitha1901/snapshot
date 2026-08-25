from fastapi import APIRouter

from app.core import config
from app.schemas.command import CommandRequest, StudioResponse
from app.services import command_dispatcher

router = APIRouter()


@router.post("/api/command", response_model=StudioResponse)
def post_command(request: CommandRequest) -> StudioResponse:
    config.ensure_repo_root_exists()
    return command_dispatcher.run_command(config.REPO_ROOT, request.input)
