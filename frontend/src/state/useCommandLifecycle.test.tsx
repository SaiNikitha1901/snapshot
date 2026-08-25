import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { makeLearnCard, makeStudioResponse } from '../test/fixtures'
import { useLearnState } from './LearnContext'
import { useRepoState } from './RepoStateContext'
import { useSelectionState } from './SelectionContext'
import { StudioProviders } from './StudioProviders'
import { useCommandLifecycle } from './useCommandLifecycle'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, runCommand: vi.fn(), generateLearnCard: vi.fn() }
})

import { generateLearnCard, runCommand } from '../api/client'

function wrapper({ children }: { children: ReactNode }) {
  return <StudioProviders>{children}</StudioProviders>
}

function useHarness() {
  return {
    lifecycle: useCommandLifecycle(),
    repo: useRepoState(),
    selection: useSelectionState(),
    learn: useLearnState(),
  }
}

describe('useCommandLifecycle', () => {
  it('walks executing -> statusUpdating -> learnUpdating -> idle for a command with no animation', async () => {
    const focusedCommit = {
      kind: 'commit' as const,
      oid: 'a'.repeat(40),
      tree_oid: 'b'.repeat(40),
      parent_oid: null,
      merge_parent_oid: null,
      author: 'Snapshot User <snapshot@example.com> 1',
      committer: 'Snapshot User <snapshot@example.com> 1',
      message: 'first commit',
      is_merge: false,
    }
    const response = makeStudioResponse({
      repository_status: makeStudioResponse().repository_status,
      focused_object: focusedCommit,
      learn: { cards: [makeLearnCard()] },
    })
    vi.mocked(runCommand).mockResolvedValue(response)
    vi.mocked(generateLearnCard).mockResolvedValue({ card: makeLearnCard(), source: 'template' })

    const { result } = renderHook(useHarness, { wrapper })
    expect(result.current.lifecycle.phase).toBe('idle')

    await act(async () => {
      await result.current.lifecycle.submit('commit -m "first commit"')
    })

    expect(result.current.lifecycle.phase).toBe('idle')
    expect(result.current.repo.status).toEqual(response.repository_status)
    expect(result.current.selection.object).toEqual(focusedCommit)
    expect(result.current.learn.entries).toHaveLength(1)
    expect(result.current.learn.entries[0].card.trigger).toBe('repository_initialized')
  })

  it('does not touch selection or learn state when the response has neither', async () => {
    vi.mocked(runCommand).mockResolvedValue(makeStudioResponse({ focused_object: null, learn: null }))

    const { result } = renderHook(useHarness, { wrapper })
    await act(async () => {
      await result.current.lifecycle.submit('ls')
    })

    expect(result.current.selection.object).toBeNull()
    expect(result.current.learn.entries).toHaveLength(0)
  })

  it('surfaces a network failure as a failed result and still returns to idle', async () => {
    vi.mocked(runCommand).mockRejectedValue(new Error('network down'))

    const { result } = renderHook(useHarness, { wrapper })
    let outcome!: Awaited<ReturnType<typeof result.current.lifecycle.submit>>
    await act(async () => {
      outcome = await result.current.lifecycle.submit('init')
    })

    expect(outcome.ok).toBe(false)
    expect(outcome.terminal.stderr_lines[0]).toContain('network down')
    expect(result.current.lifecycle.phase).toBe('idle')
  })
})
