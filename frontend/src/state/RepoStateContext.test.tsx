import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { makeGraph, makeStatus } from '../test/fixtures'
import { EMPTY_GRAPH, EMPTY_STATUS, RepoStateProvider, useRepoApi, useRepoState } from './RepoStateContext'

vi.mock('../api/client', () => ({
  getRepoStatus: vi.fn(),
  getRepoGraph: vi.fn(),
}))

import { getRepoGraph, getRepoStatus } from '../api/client'

function wrapper({ children }: { children: ReactNode }) {
  return <RepoStateProvider>{children}</RepoStateProvider>
}

function useHarness() {
  return { state: useRepoState(), api: useRepoApi() }
}

describe('RepoStateContext', () => {
  it('starts empty (never invents repository state)', () => {
    const { result } = renderHook(useHarness, { wrapper })
    expect(result.current.state.status).toEqual(EMPTY_STATUS)
    expect(result.current.state.graph).toEqual(EMPTY_GRAPH)
  })

  it('apply() replaces status and graph wholesale from a StudioResponse', () => {
    const { result } = renderHook(useHarness, { wrapper })
    const status = makeStatus({ current_branch: 'feature' })
    const graph = makeGraph({ head_commit_oid: 'a'.repeat(40) })

    act(() => result.current.api.apply(status, graph))

    expect(result.current.state.status).toEqual(status)
    expect(result.current.state.graph).toEqual(graph)
  })

  it('hydrate() fetches status and graph from the backend on demand', async () => {
    const status = makeStatus({ current_branch: 'main' })
    const graph = makeGraph()
    vi.mocked(getRepoStatus).mockResolvedValue(status)
    vi.mocked(getRepoGraph).mockResolvedValue(graph)

    const { result } = renderHook(useHarness, { wrapper })

    await act(async () => {
      await result.current.api.hydrate()
    })

    expect(result.current.state.status).toEqual(status)
    expect(result.current.state.graph).toEqual(graph)
  })
})
