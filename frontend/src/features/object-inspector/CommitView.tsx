import type { CommitObject } from '../../types/snapshot'
import { OidLink } from './OidLink'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px] font-medium tracking-wide text-fg-subtle uppercase">{label}</span>
      {children}
    </div>
  )
}

export function CommitView({ object }: { object: CommitObject }) {
  return (
    <div className="flex flex-col gap-3 p-4 text-xs">
      <div className="flex items-center gap-2 text-fg-subtle">
        commit <span className="font-mono text-fg">{object.oid}</span>
        {object.is_merge && (
          <span className="rounded-sm bg-accent-soft px-1.5 py-0.5 text-[10px] font-medium text-accent">merge</span>
        )}
      </div>

      <Field label="tree">
        <OidLink oid={object.tree_oid} />
      </Field>
      <Field label="parent">{object.parent_oid ? <OidLink oid={object.parent_oid} /> : <span className="text-fg-subtle">— (first commit)</span>}</Field>
      {object.merge_parent_oid && (
        <Field label="merge parent">
          <OidLink oid={object.merge_parent_oid} />
        </Field>
      )}
      <Field label="author">
        <span className="font-mono text-fg-muted">{object.author}</span>
      </Field>

      <div className="mt-1 rounded-md border border-border bg-canvas p-2 whitespace-pre-wrap text-fg">
        {object.message}
      </div>
    </div>
  )
}
