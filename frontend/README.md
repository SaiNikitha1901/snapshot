# Snapshot Studio — frontend

The React + TypeScript UI for [Snapshot](../README.md). See the root README for running the whole app.

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api/* to the backend on :8000
npm test         # Vitest + Testing Library
npm run lint     # oxlint
npm run build    # type-check and production build to dist/
```

Set `SNAPSHOT_API_PROXY_TARGET` to point the dev proxy at a backend other than `http://localhost:8000`. For a static build, `VITE_API_BASE_URL` is baked in at build time instead (see `Dockerfile`).

## Layout

```
src/
├── api/          typed client for the FastAPI backend
├── app/          App shell, router, and the studio layout
├── features/     one folder per panel: terminal, commit-graph, object-graph,
│                 object-animation, object-inspector, repository-status, reflog, learn
├── pages/        the landing page
├── state/        React contexts: repo state, selection, animation, learn, command lifecycle
├── styles/       design tokens (Tailwind v4 @theme) and globals
└── types/        TypeScript mirrors of the backend's response schemas
```
