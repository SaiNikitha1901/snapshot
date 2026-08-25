import { Handle, Position, type NodeProps } from 'reactflow'
import { branchColorClasses } from '../branchColor'
import type { BranchRefNodeData } from '../graphLayout'

export function BranchRefNode({ data }: NodeProps<BranchRefNodeData>) {
  const { branch } = data
  const colors = branchColorClasses(branch.lane, branch.is_current)

  return (
    <div className={`rounded-full border bg-surface px-2.5 py-1 font-mono text-[10px] ${colors.border} ${colors.text}`}>
      {branch.name}
      <Handle type="source" position={Position.Bottom} className="!h-1 !w-1 !border-0 !bg-border-strong" />
    </div>
  )
}
