import type { HeadObject } from '../../types/snapshot'
import { BranchLink, OidLink } from './OidLink'

export function HeadView({ object }: { object: HeadObject }) {
  return (
    <div className="flex flex-col gap-3 p-4 text-xs">
      <div className="flex items-center gap-2 text-fg-subtle">
        HEAD
        <span
          className={`rounded-sm px-1.5 py-0.5 text-[10px] font-medium ${
            object.detached ? 'bg-accent-soft text-accent' : 'bg-surface-raised text-fg-muted'
          }`}
        >
          {object.detached ? 'detached' : 'symbolic'}
        </span>
      </div>

      {object.detached ? (
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] font-medium tracking-wide text-fg-subtle uppercase">points directly at</span>
          {object.commit_oid ? <OidLink oid={object.commit_oid} /> : <span className="text-fg-subtle">—</span>}
        </div>
      ) : (
        <div className="flex items-center justify-between gap-2">
          <span className="text-[10px] font-medium tracking-wide text-fg-subtle uppercase">points at branch</span>
          {object.branch_name ? <BranchLink name={object.branch_name} /> : <span className="text-fg-subtle">—</span>}
        </div>
      )}
    </div>
  )
}
