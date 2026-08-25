import type {
  CommitGraph,
  HeadObject,
  LearnGenerateResponse,
  LearnGenerationContext,
  ObjectDetail,
  ObjectGraph,
  ReflogResponse,
  RepositoryStatus,
  StudioResponse,
} from '../types/snapshot'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// In dev, Vite's server.proxy forwards relative /api/* calls to the
// backend (see vite.config.ts), so this stays empty. The production
// Docker build has no such proxy in front of the static files it
// serves, so it bakes in an absolute backend URL at build time
// instead (see frontend/Dockerfile) -- the backend's CORS config
// already allows the frontend's origin for exactly this case.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

export function runCommand(input: string): Promise<StudioResponse> {
  return request<StudioResponse>('/api/command', {
    method: 'POST',
    body: JSON.stringify({ input }),
  })
}

export function getObject(oid: string): Promise<ObjectDetail> {
  return request<ObjectDetail>(`/api/objects/${oid}`)
}

export function getObjectGraph(oid: string): Promise<ObjectGraph> {
  return request<ObjectGraph>(`/api/objects/${oid}/graph`)
}

export function getBranch(name: string): Promise<ObjectDetail> {
  return request<ObjectDetail>(`/api/branches/${encodeURIComponent(name)}`)
}

export function getRepoStatus(): Promise<RepositoryStatus> {
  return request<RepositoryStatus>('/api/repo/status')
}

export function getRepoGraph(): Promise<CommitGraph> {
  return request<CommitGraph>('/api/repo/graph')
}

export function getRepoHead(): Promise<HeadObject> {
  return request<HeadObject>('/api/repo/head')
}

export function getReflog(): Promise<ReflogResponse> {
  return request<ReflogResponse>('/api/repo/reflog')
}

export function readFile(path: string): Promise<{ path: string; content: string; exists: boolean }> {
  return request(`/api/files/read?path=${encodeURIComponent(path)}`)
}

export function writeFile(path: string, content: string): Promise<StudioResponse> {
  return request<StudioResponse>('/api/files/write', {
    method: 'POST',
    body: JSON.stringify({ path, content }),
  })
}

export function generateLearnCard(context: LearnGenerationContext): Promise<LearnGenerateResponse> {
  return request<LearnGenerateResponse>('/api/learn/generate', {
    method: 'POST',
    body: JSON.stringify({ context }),
  })
}
