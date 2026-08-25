import type { BlobObject } from '../../types/snapshot'

export function BlobView({ object }: { object: BlobObject }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4 text-xs">
      <div className="text-fg-subtle">
        blob <span className="font-mono text-fg">{object.oid}</span> · {object.size} bytes
      </div>
      {object.is_binary || object.content === null ? (
        <div className="text-fg-subtle italic">binary content, not shown</div>
      ) : (
        <pre className="min-h-0 flex-1 overflow-auto rounded-sm border border-border bg-canvas p-3 font-mono text-fg whitespace-pre-wrap">
          {object.content}
        </pre>
      )}
    </div>
  )
}
