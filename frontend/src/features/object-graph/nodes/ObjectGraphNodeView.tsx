import { Handle, Position, type NodeProps } from 'reactflow'
import type { ObjectGraphNodeData } from '../objectGraphLayout'

const KIND_TAGS = { commit: 'COMMIT', tree: 'TREE', blob: 'BLOB' } as const

/** Visually mirrors commit-graph/nodes/CommitNode.tsx exactly (same
 * size, border treatment, HEAD ring, selected ring, mono accent oid)
 * so switching between the Commits and Objects tabs reads as the same
 * visual system, not a different graph. The one addition is a small
 * kind tag (COMMIT/TREE/BLOB) in place of CommitNode's HEAD-only
 * badge slot, since this view mixes three node kinds that otherwise
 * look identical. */
export function ObjectGraphNodeView({ data }: NodeProps<ObjectGraphNodeData>) {
  const { node, isSelected } = data
  const isHead = node.kind === 'commit' && node.is_head_commit

  return (
    <div
      className={`w-[132px] rounded-sm border bg-surface-raised px-2.5 py-2 text-[11px] shadow-none transition-colors ${
        isHead
          ? 'border-accent ring-1 ring-accent'
          : isSelected
            ? 'border-border-strong ring-1 ring-border-strong'
            : 'border-border'
      } ${node.kind === 'commit' && node.is_merge ? 'border-l-2 border-l-branch-blue' : ''}`}
      title={node.label}
    >
      <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
      <div className="flex items-center justify-between gap-1">
        <span className="font-mono text-accent">{node.short_oid}</span>
        <span
          className={`text-[9px] font-medium tracking-wide uppercase ${isHead ? 'text-accent' : 'text-fg-subtle'}`}
        >
          {isHead ? 'HEAD' : KIND_TAGS[node.kind]}
        </span>
      </div>
      <div className="mt-0.5 truncate text-fg-muted">{node.label}</div>
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
    </div>
  )
}
