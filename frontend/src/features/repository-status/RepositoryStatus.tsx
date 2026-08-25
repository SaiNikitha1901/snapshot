import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useRepoState } from '../../state/RepoStateContext'
import { useSelectionApi } from '../../state/SelectionContext'

type SemanticColor = 'success' | 'warning' | 'danger' | 'neutral'

// Full literal class names so Tailwind's scanner finds them even though
// they're selected dynamically at runtime.
const DOT_CLASSES: Record<SemanticColor, string> = {
  success: 'bg-success',
  warning: 'bg-warning',
  danger: 'bg-danger',
  neutral: 'bg-fg-subtle',
}
const TEXT_CLASSES: Record<SemanticColor, string> = {
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
  neutral: 'text-fg-subtle',
}

/** Briefly true right after `value` changes, then settles back to
 * false -- "Git is doing something" gets one quiet orange pulse, not
 * a permanent state. */
function useChangeFlash<T>(value: T): boolean {
  const [flashing, setFlashing] = useState(false)
  const previous = useRef(value)

  useEffect(() => {
    if (previous.current === value) return
    previous.current = value
    setFlashing(true)
    const timeout = setTimeout(() => setFlashing(false), 700)
    return () => clearTimeout(timeout)
  }, [value])

  return flashing
}

function Row({ label, children, flash = false }: { label: string; children: ReactNode; flash?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="text-[10px] font-medium tracking-wide text-fg-subtle uppercase">{label}</span>
      <span className={`text-right transition-colors duration-300 ${flash ? 'text-accent' : ''}`}>{children}</span>
    </div>
  )
}

function StatusDot({ color, label }: { color: SemanticColor; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`h-1.5 w-1.5 rounded-full transition-colors duration-300 ${DOT_CLASSES[color]}`} />
      <span className={`transition-colors duration-300 ${TEXT_CLASSES[color]}`}>{label}</span>
    </span>
  )
}

function PathList({ label, paths, color }: { label: string; paths: string[]; color: SemanticColor }) {
  return (
    <div className="text-xs">
      <div className={`mb-1 text-[10px] font-medium tracking-wide uppercase ${TEXT_CLASSES[color]}`}>
        {label} ({paths.length})
      </div>
      <ul className="space-y-0.5 pl-2 font-mono text-fg-muted">
        {paths.map((path) => (
          <li key={path} className="truncate">
            {path}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function RepositoryStatus() {
  const { status } = useRepoState()
  const selectionApi = useSelectionApi()

  const branchFlash = useChangeFlash(status.head_detached ? null : status.current_branch)
  const commitFlash = useChangeFlash(status.current_commit_oid)

  if (!status.initialized) {
    return (
      <div className="p-4 text-xs text-fg-subtle">
        No repository yet — run <span className="font-mono text-fg">init</span> in the terminal.
      </div>
    )
  }

  const changedCount = status.unstaged_paths.length + status.untracked_paths.length
  const workingDirColor: SemanticColor = status.conflicted_paths.length
    ? 'danger'
    : status.working_directory_clean
      ? 'success'
      : 'warning'
  const indexColor: SemanticColor = status.staged_paths.length ? 'warning' : 'success'

  return (
    <div className="flex flex-col gap-3 p-4">
      <Row label="HEAD" flash={branchFlash}>
        {status.head_detached ? (
          <span className="font-mono text-accent">detached</span>
        ) : (
          <span className="text-fg-muted">
            symbolic → <span className="font-mono text-accent">refs/heads/{status.current_branch}</span>
          </span>
        )}
      </Row>

      <Row label="Current Branch" flash={branchFlash}>
        {status.head_detached || !status.current_branch ? (
          <span className="text-fg-subtle">— (detached)</span>
        ) : (
          <button
            type="button"
            className="font-mono text-accent hover:underline"
            onClick={() => void selectionApi.selectBranch(status.current_branch!)}
          >
            {status.current_branch}
          </button>
        )}
      </Row>

      <Row label="Current Commit" flash={commitFlash}>
        {status.current_commit_oid ? (
          <button
            type="button"
            className="font-mono text-fg hover:underline"
            onClick={() => void selectionApi.selectByOid(status.current_commit_oid!)}
          >
            {status.current_commit_oid.slice(0, 7)}
          </button>
        ) : (
          <span className="text-fg-subtle">no commits yet</span>
        )}
      </Row>

      <Row label="Working Directory">
        <StatusDot color={workingDirColor} label={status.working_directory_clean ? 'clean' : `${changedCount} changed`} />
      </Row>

      <Row label="Index">
        <StatusDot color={indexColor} label={status.staged_paths.length ? `${status.staged_paths.length} staged` : 'empty'} />
      </Row>

      {status.conflicted_paths.length > 0 && <PathList label="Conflicted" paths={status.conflicted_paths} color="danger" />}
      {status.staged_paths.length > 0 && <PathList label="Staged" paths={status.staged_paths} color="warning" />}
      {status.unstaged_paths.length > 0 && <PathList label="Modified" paths={status.unstaged_paths} color="danger" />}
      {status.untracked_paths.length > 0 && <PathList label="Untracked" paths={status.untracked_paths} color="neutral" />}
    </div>
  )
}
