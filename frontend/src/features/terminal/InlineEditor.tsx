import { useEffect, useRef, useState } from 'react'
import { readFile } from '../../api/client'

interface InlineEditorProps {
  path: string
  onCancel: () => void
  onSave: (path: string, content: string) => Promise<void>
}

/** The terminal's only concession to file editing: there's no separate
 * editor panel in Snapshot Studio, so `edit <file>` opens this overlay
 * in place of the prompt. Deliberately a plain textarea -- no syntax
 * highlighting dependency -- since this is a staging aid, not an IDE. */
export function InlineEditor({ path, onCancel, onSave }: InlineEditorProps) {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    let cancelled = false
    readFile(path).then((result) => {
      if (!cancelled) {
        setContent(result.content)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [path])

  useEffect(() => {
    if (!loading) textareaRef.current?.focus()
  }, [loading])

  const handleSave = async () => {
    setSaving(true)
    await onSave(path, content)
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 's') {
      event.preventDefault()
      void handleSave()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      onCancel()
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 p-2">
      <div className="flex shrink-0 items-center justify-between text-xs text-fg-muted">
        <span className="font-mono text-fg">
          edit <span className="text-accent">{path}</span>
        </span>
        <span>⌘S save · Esc cancel</span>
      </div>
      <textarea
        ref={textareaRef}
        className="min-h-0 flex-1 resize-none rounded-md border border-border bg-canvas p-2 font-mono text-sm text-fg outline-none focus:border-border-strong disabled:opacity-60"
        value={loading ? 'Loading…' : content}
        disabled={loading || saving}
        onChange={(e) => setContent(e.target.value)}
        onKeyDown={handleKeyDown}
        spellCheck={false}
      />
      <div className="flex shrink-0 justify-end gap-2">
        <button
          type="button"
          className="rounded-md border border-border px-3 py-1 text-xs text-fg-muted hover:border-border-strong hover:text-fg"
          onClick={onCancel}
          disabled={saving}
        >
          Cancel
        </button>
        <button
          type="button"
          className="rounded-md border border-accent bg-accent-soft px-3 py-1 text-xs text-accent hover:bg-accent hover:text-accent-fg disabled:opacity-60"
          onClick={() => void handleSave()}
          disabled={loading || saving}
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  )
}
