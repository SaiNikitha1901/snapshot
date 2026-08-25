import { Handle, Position, type NodeProps } from 'reactflow'
import type { CommitNodeData } from '../graphLayout'

export function CommitNode({ data }: NodeProps<CommitNodeData>) {
  const { commit, isSelected } = data

  return (
    <div
      className={`w-[132px] rounded-sm border bg-surface-raised px-2.5 py-2 text-[11px] shadow-none transition-colors ${
        commit.is_head_commit
          ? 'border-accent ring-1 ring-accent'
          : isSelected
            ? 'border-border-strong ring-1 ring-border-strong'
            : 'border-border'
      } ${commit.is_merge ? 'border-l-2 border-l-branch-blue' : ''}`}
      title={commit.message_summary}
    >
      <Handle type="target" position={Position.Left} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
      <div className="flex items-center justify-between gap-1">
        <span className="font-mono text-accent">{commit.short_oid}</span>
        {commit.is_head_commit && <span className="text-[9px] font-medium tracking-wide text-accent uppercase">HEAD</span>}
      </div>
      <div className="mt-0.5 truncate text-fg-muted">{commit.message_summary || '(empty message)'}</div>
      <Handle type="source" position={Position.Right} className="!h-1.5 !w-1.5 !border-0 !bg-border-strong" />
    </div>
  )
}
