import { useEffect, useState } from 'react'
import { getReflog } from '../../api/client'
import { useSelectionApi } from '../../state/SelectionContext'
import type { ReflogEntry } from '../../types/snapshot'

interface ReflogViewProps {
  /** Lets a row hand its commit off to the Object Graph tab -- owned
   * by VisualizationPanel, which already tracks the last-selected
   * commit for ObjectGraph via the shared selection. */
  onViewInGraph: (oid: string) => void
}

/** The object-level counterpart to ObjectGraph.tsx: same
 * fetch-on-mount shape, but a compact list rather than a graph --
 * "a small, elegant Reflog view, not another dashboard." Every entry
 * is a real HEAD movement in the order Snapshot recorded it, newest
 * first, independent of what the commit graph currently considers
 * reachable. */
export function ReflogView({ onViewInGraph }: ReflogViewProps) {
  const [entries, setEntries] = useState<ReflogEntry[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const selectionApi = useSelectionApi()

  /* eslint-disable react/set-state-in-effect */
  useEffect(() => {
    let cancelled = false
    getReflog()
      .then((result) => {
        if (!cancelled) setEntries(result.entries)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load reflog')
      })
    return () => {
      cancelled = true
    }
  }, [])
  /* eslint-enable react/set-state-in-effect */

  if (error) {
    return <div className="p-4 text-xs text-danger">{error}</div>
  }

  if (!entries) {
    return <div className="p-4 text-xs text-fg-subtle">Loading…</div>
  }

  if (entries.length === 0) {
    return (
      <div className="p-4 text-xs text-fg-subtle">
        No HEAD movements recorded yet. The reflog fills in as you{' '}
        <span className="font-mono text-fg">commit</span>, <span className="font-mono text-fg">checkout</span>, and{' '}
        <span className="font-mono text-fg">merge</span>.
      </div>
    )
  }

  return (
    <ul className="divide-y divide-border">
      {entries.map((entry) => (
        <li key={entry.index} className="flex items-center gap-2 px-4 py-2 transition-colors hover:bg-surface-raised">
          <button
            type="button"
            className="flex min-w-0 flex-1 items-center gap-2 text-left text-xs"
            onClick={() => void selectionApi.selectByOid(entry.new_oid)}
          >
            <span className="shrink-0 font-mono text-[10px] text-fg-subtle">{`HEAD@{${entry.index}}`}</span>
            <span className="shrink-0 rounded-sm bg-surface-raised px-1.5 py-0.5 font-mono text-accent">
              {entry.short_new_oid}
            </span>
            <span className="min-w-0 flex-1 truncate text-fg-muted">{entry.message}</span>
            {!entry.is_reachable && (
              <span className="shrink-0 rounded-sm bg-danger-soft px-1.5 py-0.5 text-[10px] font-medium tracking-wide text-danger uppercase">
                unreachable
              </span>
            )}
          </button>
          <button
            type="button"
            className="shrink-0 text-[10px] tracking-wide text-fg-subtle uppercase hover:text-accent"
            onClick={() => onViewInGraph(entry.new_oid)}
          >
            View graph
          </button>
        </li>
      ))}
    </ul>
  )
}
