# Snapshot

> **Watch Git Think.**

Snapshot is a Git implementation built from scratch to explain how Git actually works. Instead of memorizing commands, you can inspect the real objects, refs, and HEAD movements Snapshot creates as you use it — either from a CLI, or visually in **Snapshot Studio**, a web UI that shows the commit graph, the object graph, and the reflog live as you type commands.

Snapshot is not a Git wrapper — every object store, hash, tree, commit, branch, merge, and reflog entry is implemented from first principles in Python.

## Quick start

```bash
docker compose up --build
```

Open **http://localhost:5173**. The backend runs on :8000, and a Docker volume persists your repository across restarts. No API key is required — `GEMINI_API_KEY=your-key docker compose up --build` enables richer, AI-generated explanations in the Learn panel, but everything works without one.

## What's included

**The engine** (`src/snapshot/`) — a real content-addressable object store (SHA-1, blobs, trees, commits), branches, checkout (including detached HEAD), three-way merge with conflict detection, and an append-only reflog, all reachable through a `snapshot` CLI:

```bash
pip install -e .
snapshot init
snapshot add .
snapshot commit -m "first commit"
snapshot branch feature && snapshot checkout feature
snapshot merge feature
snapshot log
snapshot reflog
```

**Snapshot Studio** (`backend/` + `frontend/`) — a FastAPI backend wrapping the engine, and a React + TypeScript frontend that turns every command into a live commit graph, object graph, and reflog, plus panels for repository status, object inspection, and inline explanations of what Git just did internally and why.

## Running without Docker

```bash
# backend
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload

# frontend, in a second terminal
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 — Vite proxies `/api/*` to the backend on :8000.

## Tests

```bash
pytest tests backend/tests -v   # engine + backend
cd frontend && npm test         # frontend
```

## Project structure

```
src/snapshot/     the engine: object storage, refs, checkout, merge, reflog, CLI
tests/            engine unit tests
backend/          FastAPI wrapper exposing the engine over HTTP
frontend/         Snapshot Studio (React + TypeScript + React Flow)
```

## Intentional simplifications

Snapshot focuses on the object model and repository mechanics, not production performance or the full Git surface. It does not implement remotes, packfiles, delta compression, garbage collection, rebase, cherry-pick, hooks, tags, sparse checkout, or worktrees — and per-branch reflogs are simplified to a single HEAD reflog. Every simplification like this is called out in Studio's Learn panel where it's relevant, rather than hidden.

## License

This project is intended for educational purposes.
