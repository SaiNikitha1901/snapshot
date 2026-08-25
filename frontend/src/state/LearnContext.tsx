import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { generateLearnCard } from '../api/client'
import type { LearnCard } from '../types/snapshot'

export interface LearnCardEntry {
  card: LearnCard
  source: 'template' | 'gemini' | 'loading'
}

interface LearnState {
  entries: LearnCardEntry[]
}

interface LearnApi {
  /** Sets the deterministic cards from a StudioResponse, then asks the
   * backend to enrich each one via Gemini in the background. */
  setCards: (cards: LearnCard[]) => void
  clear: () => void
}

const LearnStateCtx = createContext<LearnState | null>(null)
const LearnApiCtx = createContext<LearnApi | null>(null)

export function LearnProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<LearnCardEntry[]>([])

  const setCards = useCallback((cards: LearnCard[]) => {
    setEntries(cards.map((card) => ({ card, source: 'template' as const })))

    cards.forEach((card, index) => {
      if (!card.generation_context) return
      setEntries((prev) => {
        if (prev[index]?.card.trigger !== card.trigger) return prev
        const next = [...prev]
        next[index] = { ...next[index], source: 'loading' }
        return next
      })

      generateLearnCard(card.generation_context)
        .then((response) => {
          setEntries((prev) => {
            if (prev[index]?.card.trigger !== card.trigger) return prev
            const next = [...prev]
            next[index] = { card: response.card, source: response.source }
            return next
          })
        })
        .catch(() => {
          setEntries((prev) => {
            if (prev[index]?.card.trigger !== card.trigger) return prev
            const next = [...prev]
            next[index] = { ...next[index], source: 'template' }
            return next
          })
        })
    })
  }, [])

  const clear = useCallback(() => setEntries([]), [])

  const state = useMemo(() => ({ entries }), [entries])
  const api = useMemo(() => ({ setCards, clear }), [setCards, clear])

  return (
    <LearnStateCtx.Provider value={state}>
      <LearnApiCtx.Provider value={api}>{children}</LearnApiCtx.Provider>
    </LearnStateCtx.Provider>
  )
}

export function useLearnState(): LearnState {
  const ctx = useContext(LearnStateCtx)
  if (!ctx) throw new Error('useLearnState must be used within LearnProvider')
  return ctx
}

export function useLearnApi(): LearnApi {
  const ctx = useContext(LearnApiCtx)
  if (!ctx) throw new Error('useLearnApi must be used within LearnProvider')
  return ctx
}
