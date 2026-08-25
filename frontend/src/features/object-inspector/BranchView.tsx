import type { BranchObject } from '../../types/snapshot'
import { OidLink } from './OidLink'

export function BranchView({ object }: { object: BranchObject }) {
  return (
    <div className="flex flex-col gap-3 p-4 text-xs">
      <div className="flex items-center gap-2 text-fg-subtle">
        branch <span className="font-mono text-accent">{object.name}</span>
        {object.is_current && (
          <span className="rounded-sm bg-accent-soft px-1.5 py-0.5 text-[10px] font-medium text-accent">current</span>
        )}
      </div>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-medium tracking-wide text-fg-subtle uppercase">points at</span>
        {object.commit_oid ? <OidLink oid={object.commit_oid} /> : <span className="text-fg-subtle">— (no commits yet)</span>}
      </div>
    </div>
  )
}
