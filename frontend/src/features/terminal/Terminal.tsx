import { useEffect, useRef } from 'react'
import { InlineEditor } from './InlineEditor'
import type { ScrollbackEntry } from './useTerminal'
import { useTerminal } from './useTerminal'

function EntryView({ entry }: { entry: ScrollbackEntry }) {
  return (
    <div className="mb-3 animate-[fadein_0.25s_ease-out]">
      <div className="flex gap-2">
        <span className="text-accent select-none">❯</span>
        <span className="whitespace-pre-wrap text-fg">{entry.input}</span>
      </div>
      {entry.stdoutLines.map((line, i) => (
        <div key={`o${i}`} className="pl-4 whitespace-pre-wrap text-fg-muted">
          {line.length === 0 ? ' ' : line}
        </div>
      ))}
      {entry.stderrLines.map((line, i) => (
        <div key={`e${i}`} className="pl-4 whitespace-pre-wrap text-danger">
          {line}
        </div>
      ))}
    </div>
  )
}

export function Terminal() {
  const terminal = useTerminal()
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [terminal.entries, terminal.editingFile])

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      if (terminal.isBusy) return
      void terminal.submit(terminal.inputValue)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      terminal.historyUp()
    } else if (event.key === 'ArrowDown') {
      event.preventDefault()
      terminal.historyDown()
    } else if (event.key === 'Tab') {
      event.preventDefault()
      const input = event.currentTarget
      const completed = terminal.autocomplete(input.selectionStart ?? terminal.inputValue.length)
      terminal.setInputValue(completed)
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col font-mono text-[13px]" onClick={() => inputRef.current?.focus()}>
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
        {terminal.entries.map((entry) => (
          <EntryView key={entry.id} entry={entry} />
        ))}

        {terminal.editingFile ? (
          <InlineEditor path={terminal.editingFile} onCancel={terminal.closeEditor} onSave={terminal.saveEditor} />
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-accent select-none">❯</span>
            <input
              ref={inputRef}
              className="flex-1 bg-transparent text-fg outline-none disabled:opacity-50"
              value={terminal.inputValue}
              onChange={(e) => terminal.setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={terminal.isBusy}
              autoFocus
              spellCheck={false}
              autoComplete="off"
              autoCapitalize="off"
            />
            {terminal.isBusy && <span className="text-fg-subtle">Running…</span>}
          </div>
        )}
      </div>
    </div>
  )
}
