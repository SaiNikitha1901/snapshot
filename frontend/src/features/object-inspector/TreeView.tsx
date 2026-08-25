import type { TreeObject } from '../../types/snapshot'
import { OidLink } from './OidLink'

export function TreeView({ object }: { object: TreeObject }) {
  return (
    <div className="flex flex-col gap-3 p-4 text-xs">
      <div className="text-fg-subtle">
        tree <span className="font-mono text-fg">{object.oid}</span> · {object.entries.length}{' '}
        {object.entries.length === 1 ? 'entry' : 'entries'}
      </div>
      <ul className="flex flex-col gap-1">
        {object.entries.map((entry) => (
          <li key={entry.name} className="flex items-center justify-between gap-2 rounded-md bg-surface-raised px-2 py-1">
            <span className="flex items-center gap-2 font-mono">
              <span className="w-8 shrink-0 text-[10px] text-fg-subtle uppercase">{entry.type}</span>
              <span className="text-fg">{entry.name}</span>
            </span>
            <OidLink oid={entry.oid} />
          </li>
        ))}
      </ul>
    </div>
  )
}
