"""Backend configuration: environment-driven, single shared workspace.

Snapshot Studio runs as a single shared workspace (one repository on
backend disk), matching the engine's existing single-repo assumption
and the desktop/local-tool framing described in the product spec. No
per-session isolation, no auth.
"""

import os
from pathlib import Path

# The one repository Snapshot Studio operates on. Overridable so Docker
# Compose can point it at a mounted volume.
REPO_ROOT = Path(os.environ.get("SNAPSHOT_REPO_ROOT", Path(__file__).resolve().parents[3] / "workspace"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

CORS_ALLOW_ORIGINS = os.environ.get("SNAPSHOT_CORS_ORIGINS", "http://localhost:5173").split(",")


def snapshot_dir() -> Path:
    return REPO_ROOT / ".snapshot"


def objects_dir() -> Path:
    return snapshot_dir() / "objects"


def index_path() -> Path:
    return snapshot_dir() / "index"


def ensure_repo_root_exists() -> None:
    REPO_ROOT.mkdir(parents=True, exist_ok=True)
