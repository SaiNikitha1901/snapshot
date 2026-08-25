import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { getRepoGraph, getRepoStatus } from '../api/client'
import type { CommitGraph, RepositoryStatus } from '../types/snapshot'

export const EMPTY_STATUS: RepositoryStatus = {
  initialized: false,
  head_detached: false,
  current_branch: null,
  current_commit_oid: null,
  working_directory_clean: true,
  staged_paths: [],
  unstaged_paths: [],
  untracked_paths: [],
  conflicted_paths: [],
}

export const EMPTY_GRAPH: CommitGraph = {
  commits: [],
  branches: [],
  head_detached: false,
  head_commit_oid: null,
}

interface RepoState {
  status: RepositoryStatus
  graph: CommitGraph
}

interface RepoApi {
  apply: (status: RepositoryStatus, graph: CommitGraph) => void
  hydrate: () => Promise<void>
}

const RepoStateCtx = createContext<RepoState | null>(null)
const RepoApiCtx = createContext<RepoApi | null>(null)

export function RepoStateProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState(EMPTY_STATUS)
  const [graph, setGraph] = useState(EMPTY_GRAPH)

  const apply = useCallback((nextStatus: RepositoryStatus, nextGraph: CommitGraph) => {
    setStatus(nextStatus)
    setGraph(nextGraph)
  }, [])

  const hydrate = useCallback(async () => {
    const [nextStatus, nextGraph] = await Promise.all([getRepoStatus(), getRepoGraph()])
    setStatus(nextStatus)
    setGraph(nextGraph)
  }, [])

  const state = useMemo(() => ({ status, graph }), [status, graph])
  const api = useMemo(() => ({ apply, hydrate }), [apply, hydrate])

  return (
    <RepoStateCtx.Provider value={state}>
      <RepoApiCtx.Provider value={api}>{children}</RepoApiCtx.Provider>
    </RepoStateCtx.Provider>
  )
}

export function useRepoState(): RepoState {
  const ctx = useContext(RepoStateCtx)
  if (!ctx) throw new Error('useRepoState must be used within RepoStateProvider')
  return ctx
}

export function useRepoApi(): RepoApi {
  const ctx = useContext(RepoApiCtx)
  if (!ctx) throw new Error('useRepoApi must be used within RepoStateProvider')
  return ctx
}
