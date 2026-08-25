import { useSelectionApi } from '../../state/SelectionContext'

export function OidLink({ oid, label }: { oid: string; label?: string }) {
  const selectionApi = useSelectionApi()
  return (
    <button
      type="button"
      className="rounded-sm bg-surface-raised px-1.5 py-0.5 font-mono text-accent hover:underline"
      onClick={() => void selectionApi.selectByOid(oid)}
    >
      {label ?? oid.slice(0, 7)}
    </button>
  )
}

export function BranchLink({ name }: { name: string }) {
  const selectionApi = useSelectionApi()
  return (
    <button
      type="button"
      className="rounded-sm bg-surface-raised px-1.5 py-0.5 font-mono text-accent hover:underline"
      onClick={() => void selectionApi.selectBranch(name)}
    >
      {name}
    </button>
  )
}
