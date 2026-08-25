/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Absolute backend URL to call instead of relative /api/* paths.
   * Empty in dev (Vite's server.proxy handles it); set at build time
   * for the production Docker image (see frontend/Dockerfile). */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
