# Snapshot

> **Watch Git Think.**

[![CI](https://github.com/SaiNikitha1901/snapshot/actions/workflows/ci.yml/badge.svg)](https://github.com/SaiNikitha1901/snapshot/actions/workflows/ci.yml)
![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB)
![React + TypeScript](https://img.shields.io/badge/react-19%20%2B%20TypeScript-61DAFB)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Snapshot is a Git implementation built from scratch to explain how Git actually works. Instead of memorizing commands, you can inspect the real objects, refs, and HEAD movements Snapshot creates as you use it — either from a CLI, or visually in **Snapshot Studio**, a web UI that shows the commit graph, the object graph, and the reflog live as you type commands.

Snapshot is not a Git wrapper — every object store, hash, tree, commit, branch, merge, and reflog entry is implemented from first principles in Python. And because it follows Git's on-disk formats exactly, **real Git can read what Snapshot writes**.

## Quick start

```bash
docker compose up --build
```

Open **http://localhost:5173**. The backend runs on :8000, and a Docker volume persists your repository across restarts. No API key is required — `GEMINI_API_KEY=your-key docker compose up --build` enables richer, AI-generated explanations in the Learn panel, but everything works without one.

## What's included

### The engine — `src/snapshot/`

A content-addressable object store and the repository mechanics built on top of it:

- **Objects** — blobs, trees, and commits, hashed as SHA-1 over Git's `"<type> <size>\0<content>"` framing and stored zlib-compressed under `objects/xx/yyyy…`
- **Staging index** and recursive **tree building** from it, with regular and executable file modes
- **Commits and history** — parent links, `log`, and `rev-parse`
- **Branches and checkout** — symbolic and detached HEAD, with a safety check that refuses to overwrite uncommitted work
- **Merge** — merge-base discovery over the commit DAG, fast-forward, and a line-level three-way merge that writes conflict markers when both sides change the same lines
- **Reflog** — an append-only log of every HEAD movement, so "lost" commits stay recoverable

All of it is reachable through a `snapshot` CLI:

```bash
pip install -e .
snapshot init
snapshot add .
snapshot commit -m "first commit"
snapshot branch feature && snapshot checkout feature
snapshot checkout main && snapshot merge feature
snapshot log
snapshot reflog
snapshot cat-file <oid>    # also: hash-object, write-tree, ls-tree, show-index, rev-parse
```

### Snapshot Studio — `backend/` + `frontend/`

A FastAPI backend wrapping the engine, and a React + TypeScript frontend that turns every command into something you can see:

- **Terminal** with tab completion, command history, and file commands (`echo`, `cat`, `ls`, `touch`, `edit`, …) so you never leave the page
- **Commit graph** — branches, HEAD, and merges laid out live with React Flow
- **Object graph** — the commit → tree → blob structure behind any commit
- **Step-by-step animations** of what each command did internally (hash a blob, write a tree, move a ref), with adjustable speed
- **Object inspector** — click any OID to see its decoded contents and follow links between objects
- **Repository status** — working directory vs. index vs. HEAD
- **Reflog view**, including commits that no branch points to anymore
- **Learn panel** — after each command, a card explaining what Git just did, why it's designed that way, and how production Git differs. Cards are deterministic templates; with a Gemini API key they're enriched by an LLM, and fall back to the templates on any failure

## Git compatibility

Snapshot's blobs, trees, and commits are byte-for-byte what Git would write, so the same content produces the same object IDs. You can check this yourself:

```bash
mkdir demo && cd demo
echo hello > a.txt
snapshot init && snapshot add . && snapshot commit -m "hello"

git init -q && cp -R .snapshot/objects/. .git/objects/
git cat-file -p "$(snapshot rev-parse HEAD)"    # real Git reads Snapshot's commit

echo .snapshot >> .git/info/exclude
git add . && git write-tree                     # the same tree OID as the "tree" line above
```

`tests/test_git_compatibility.py` automates this. It builds a history with nested directories, an executable file, a branch, and a merge commit, then runs `git fsck --strict` over the result and checks that Snapshot's tree OIDs match `git write-tree`.

## Running without Docker

```bash
# backend
pip install -e . -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload

# frontend, in a second terminal
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 — Vite proxies `/api/*` to the backend on :8000.

## Tests

```bash
pip install -e ".[dev]" -r backend/requirements.txt
pytest                          # engine + backend
cd frontend && npm test         # frontend
```

CI runs both suites, the frontend linter, and a production build on every push.

## Project structure

```
src/snapshot/     the engine: object storage, index, trees, commits, refs, checkout, merge, reflog, CLI
tests/            engine unit tests, plus the Git compatibility suite
backend/          FastAPI wrapper exposing the engine over HTTP (command, repo, objects, files, learn APIs)
frontend/         Snapshot Studio (React + TypeScript + React Flow + Tailwind)
```

## Intentional simplifications

Snapshot focuses on the object model and repository mechanics, not production performance or the full Git surface. It does not implement remotes, packfiles, delta compression, garbage collection, rebase, cherry-pick, hooks, tags, sparse checkout, or worktrees. Per-branch reflogs are simplified to a single HEAD reflog, commits use one static author identity in UTC, and the index is a readable text file rather than Git's binary format. Every simplification like this is called out in Studio's Learn panel where it's relevant, rather than hidden.

## License

[MIT](LICENSE)
