from fastapi import APIRouter, HTTPException

from app.core import config
from app.schemas.graph import CommitGraph
from app.schemas.objects import HeadObject
from app.schemas.reflog import ReflogResponse
from app.schemas.status import RepositoryStatus
from app.services import graph_builder, object_serializer, reflog_service, status_builder

router = APIRouter()


@router.get("/api/repo/status", response_model=RepositoryStatus)
def get_status() -> RepositoryStatus:
    config.ensure_repo_root_exists()
    return status_builder.build_status(config.snapshot_dir(), config.objects_dir(), config.index_path(), config.REPO_ROOT)


@router.get("/api/repo/graph", response_model=CommitGraph)
def get_graph() -> CommitGraph:
    config.ensure_repo_root_exists()
    return graph_builder.build_graph(config.snapshot_dir(), config.objects_dir())


@router.get("/api/repo/reflog", response_model=ReflogResponse)
def get_reflog() -> ReflogResponse:
    config.ensure_repo_root_exists()
    return reflog_service.build_reflog(config.snapshot_dir(), config.objects_dir())


@router.get("/api/repo/head", response_model=HeadObject)
def get_head() -> HeadObject:
    config.ensure_repo_root_exists()
    snapshot_dir = config.snapshot_dir()
    if not (snapshot_dir / "HEAD").exists():
        raise HTTPException(status_code=404, detail="repository not initialized -- run 'init' first")
    return object_serializer.get_head_detail(snapshot_dir)
