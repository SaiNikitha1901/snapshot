import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { getBranch, getObject, getRepoHead } from '../api/client'
import type { ObjectDetail } from '../types/snapshot'

interface SelectionState {
  object: ObjectDetail | null
  loading: boolean
  error: string | null
}

interface SelectionApi {
  select: (object: ObjectDetail) => void
  selectByOid: (oid: string) => Promise<void>
  selectBranch: (name: string) => Promise<void>
  selectHead: () => Promise<void>
  clear: () => void
}

const SelectionStateCtx = createContext<SelectionState | null>(null)
const SelectionApiCtx = createContext<SelectionApi | null>(null)

export function SelectionProvider({ children }: { children: ReactNode }) {
  const [object, setObject] = useState<ObjectDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const select = useCallback((next: ObjectDetail) => {
    setObject(next)
    setError(null)
  }, [])

  const runFetch = useCallback(async (fetcher: () => Promise<ObjectDetail>) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetcher()
      setObject(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load object')
    } finally {
      setLoading(false)
    }
  }, [])

  const selectByOid = useCallback((oid: string) => runFetch(() => getObject(oid)), [runFetch])
  const selectBranch = useCallback((name: string) => runFetch(() => getBranch(name)), [runFetch])
  const selectHead = useCallback(() => runFetch(() => getRepoHead()), [runFetch])
  const clear = useCallback(() => {
    setObject(null)
    setError(null)
  }, [])

  const state = useMemo(() => ({ object, loading, error }), [object, loading, error])
  const api = useMemo(
    () => ({ select, selectByOid, selectBranch, selectHead, clear }),
    [select, selectByOid, selectBranch, selectHead, clear],
  )

  return (
    <SelectionStateCtx.Provider value={state}>
      <SelectionApiCtx.Provider value={api}>{children}</SelectionApiCtx.Provider>
    </SelectionStateCtx.Provider>
  )
}

export function useSelectionState(): SelectionState {
  const ctx = useContext(SelectionStateCtx)
  if (!ctx) throw new Error('useSelectionState must be used within SelectionProvider')
  return ctx
}

export function useSelectionApi(): SelectionApi {
  const ctx = useContext(SelectionApiCtx)
  if (!ctx) throw new Error('useSelectionApi must be used within SelectionProvider')
  return ctx
}
