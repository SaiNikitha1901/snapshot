import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type { AnimationSequence } from '../types/snapshot'

export type AnimationSpeed = 0.5 | 1 | 2

export const STEP_DURATION_MS = 900
export const FINAL_PAUSE_MS = 650

interface AnimationState {
  sequence: AnimationSequence | null
  currentStepIndex: number
  speed: AnimationSpeed
}

interface AnimationApi {
  playSequence: (sequence: AnimationSequence) => Promise<void>
  setSpeed: (speed: AnimationSpeed) => void
}

const AnimationStateCtx = createContext<AnimationState | null>(null)
const AnimationApiCtx = createContext<AnimationApi | null>(null)

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function AnimationProvider({ children }: { children: ReactNode }) {
  const [sequence, setSequence] = useState<AnimationSequence | null>(null)
  const [currentStepIndex, setCurrentStepIndex] = useState(-1)
  const [speed, setSpeedState] = useState<AnimationSpeed>(1)
  const speedRef = useRef(speed)
  useEffect(() => {
    speedRef.current = speed
  }, [speed])

  const playSequence = useCallback(async (nextSequence: AnimationSequence) => {
    if (nextSequence.steps.length === 0) return

    setSequence(nextSequence)
    for (let i = 0; i < nextSequence.steps.length; i += 1) {
      setCurrentStepIndex(i)
      // eslint-disable-next-line no-await-in-loop -- steps must play in order, mechanically
      await delay(STEP_DURATION_MS / speedRef.current)
    }
    await delay(FINAL_PAUSE_MS / speedRef.current)
    setSequence(null)
    setCurrentStepIndex(-1)
  }, [])

  const setSpeed = useCallback((next: AnimationSpeed) => setSpeedState(next), [])

  const state = useMemo(() => ({ sequence, currentStepIndex, speed }), [sequence, currentStepIndex, speed])
  const api = useMemo(() => ({ playSequence, setSpeed }), [playSequence, setSpeed])

  return (
    <AnimationStateCtx.Provider value={state}>
      <AnimationApiCtx.Provider value={api}>{children}</AnimationApiCtx.Provider>
    </AnimationStateCtx.Provider>
  )
}

export function useAnimationState(): AnimationState {
  const ctx = useContext(AnimationStateCtx)
  if (!ctx) throw new Error('useAnimationState must be used within AnimationProvider')
  return ctx
}

export function useAnimationApi(): AnimationApi {
  const ctx = useContext(AnimationApiCtx)
  if (!ctx) throw new Error('useAnimationApi must be used within AnimationProvider')
  return ctx
}
