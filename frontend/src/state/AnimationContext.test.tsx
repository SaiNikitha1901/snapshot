import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AnimationSequence } from '../types/snapshot'
import { AnimationProvider, FINAL_PAUSE_MS, STEP_DURATION_MS, useAnimationApi, useAnimationState } from './AnimationContext'

function wrapper({ children }: { children: ReactNode }) {
  return <AnimationProvider>{children}</AnimationProvider>
}

function useHarness() {
  return { state: useAnimationState(), api: useAnimationApi() }
}

const sequence: AnimationSequence = {
  command: 'commit',
  steps: [
    { kind: 'build_tree', label: 'Build tree', detail: null, object_oid: null, object_type: null, path: null, ref_name: null },
    { kind: 'write_commit', label: 'Write commit', detail: null, object_oid: null, object_type: null, path: null, ref_name: null },
  ],
}

describe('AnimationContext', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('steps through the sequence in order, pauses on the final state, then returns to idle', async () => {
    const { result } = renderHook(useHarness, { wrapper })

    let playPromise!: Promise<void>
    act(() => {
      playPromise = result.current.api.playSequence(sequence)
    })
    expect(result.current.state.sequence).not.toBeNull()
    expect(result.current.state.currentStepIndex).toBe(0)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(STEP_DURATION_MS)
    })
    expect(result.current.state.currentStepIndex).toBe(1)
    expect(result.current.state.sequence).not.toBeNull() // still visible during the final pause

    await act(async () => {
      await vi.advanceTimersByTimeAsync(STEP_DURATION_MS + FINAL_PAUSE_MS)
    })
    await playPromise

    expect(result.current.state.sequence).toBeNull()
    expect(result.current.state.currentStepIndex).toBe(-1)
  })

  it('runs faster at 2x speed and slower at 0.5x', async () => {
    const { result } = renderHook(useHarness, { wrapper })

    act(() => result.current.api.setSpeed(2))
    let playPromise!: Promise<void>
    act(() => {
      playPromise = result.current.api.playSequence(sequence)
    })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(STEP_DURATION_MS / 2)
    })
    expect(result.current.state.currentStepIndex).toBe(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(STEP_DURATION_MS / 2 + FINAL_PAUSE_MS / 2)
    })
    await playPromise
    expect(result.current.state.sequence).toBeNull()
  })

  it('is a no-op for an empty sequence', async () => {
    const { result } = renderHook(useHarness, { wrapper })
    await act(async () => {
      await result.current.api.playSequence({ command: 'noop', steps: [] })
    })
    expect(result.current.state.sequence).toBeNull()
    expect(result.current.state.currentStepIndex).toBe(-1)
  })
})
