from fastapi import APIRouter, HTTPException
from snapshot import refs as refs_mod

from app.core import config
from app.schemas.object_graph import ObjectGraph
from app.schemas.objects import BranchObject, ObjectDetail
from app.services import object_graph_builder, object_serializer

router = APIRouter()


@router.get("/api/objects/{oid}", response_model=ObjectDetail)
def get_object(oid: str) -> ObjectDetail:
    try:
        return object_serializer.get_object_detail(config.objects_dir(), oid)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/objects/{oid}/graph", response_model=ObjectGraph)
def get_object_graph(oid: str) -> ObjectGraph:
    try:
        return object_graph_builder.build_object_graph(config.snapshot_dir(), config.objects_dir(), oid)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/branches/{name}", response_model=BranchObject)
def get_branch(name: str) -> BranchObject:
    snapshot_dir = config.snapshot_dir()
    if not refs_mod.branch_exists(snapshot_dir, name):
        raise HTTPException(status_code=404, detail=f"branch '{name}' does not exist")
    return object_serializer.get_branch_detail(snapshot_dir, name)
