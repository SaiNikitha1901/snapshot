from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_command, routes_files, routes_learn, routes_objects, routes_repo
from app.core import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_repo_root_exists()
    yield


app = FastAPI(title="Snapshot Studio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_command.router)
app.include_router(routes_objects.router)
app.include_router(routes_repo.router)
app.include_router(routes_files.router)
app.include_router(routes_learn.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
