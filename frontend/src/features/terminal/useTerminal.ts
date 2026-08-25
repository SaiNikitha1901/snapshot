import { useCallback, useMemo, useRef, useState } from 'react'
import { writeFile } from '../../api/client'
import { useRepoApi, useRepoState } from '../../state/RepoStateContext'
import { useCommandLifecycle } from '../../state/useCommandLifecycle'
import { HELP_LINES } from './builtinCommands'
import { completeInput } from './completion'

export interface ScrollbackEntry {
  id: number
  input: string
  stdoutLines: string[]
  stderrLines: string[]
  exitCode: number
}

let nextEntryId = 1

export function useTerminal() {
  const lifecycle = useCommandLifecycle()
  const repoApi = useRepoApi()
  const { status, graph } = useRepoState()

  const [entries, setEntries] = useState<ScrollbackEntry[]>([])
  const [inputValue, setInputValue] = useState('')
  const [inputHistory, setInputHistory] = useState<string[]>([])
  const [, setHistoryIndex] = useState<number | null>(null)
  const [editingFile, setEditingFile] = useState<string | null>(null)
  const draftRef = useRef('')

  const appendEntry = useCallback(
    (input: string, stdoutLines: string[], stderrLines: string[], exitCode: number) => {
      setEntries((prev) => [...prev, { id: nextEntryId++, input, stdoutLines, stderrLines, exitCode }])
    },
    [],
  )

  const knownPaths = useMemo(
    () => [...status.staged_paths, ...status.unstaged_paths, ...status.untracked_paths],
    [status.staged_paths, status.unstaged_paths, status.untracked_paths],
  )

  const submit = useCallback(
    async (raw: string) => {
      const trimmed = raw.trim()
      setInputValue('')
      setHistoryIndex(null)

      if (trimmed.length > 0) {
        setInputHistory((prev) => [...prev, raw])
      }

      const name = trimmed.split(/\s+/)[0] ?? ''

      if (name === 'clear') {
        setEntries([])
        return
      }
      if (name === 'help') {
        appendEntry(raw, HELP_LINES, [], 0)
        return
      }
      if (name === 'history') {
        appendEntry(raw, inputHistory.map((cmd, i) => `${i + 1}  ${cmd}`), [], 0)
        return
      }
      if (name === 'edit') {
        const target = trimmed.split(/\s+/)[1]
        if (!target) {
          appendEntry(raw, [], ['usage: edit <file>'], 1)
          return
        }
        setEditingFile(target)
        return
      }
      if (trimmed.length === 0) {
        appendEntry(raw, [], [], 0)
        return
      }

      const result = await lifecycle.submit(raw)
      appendEntry(raw, result.terminal.stdout_lines, result.terminal.stderr_lines, result.terminal.exit_code)
    },
    [appendEntry, inputHistory, lifecycle],
  )

  const closeEditor = useCallback(() => setEditingFile(null), [])

  const saveEditor = useCallback(
    async (path: string, content: string) => {
      const response = await writeFile(path, content)
      appendEntry(
        `edit ${path}`,
        response.terminal.stdout_lines,
        response.terminal.stderr_lines,
        response.terminal.exit_code,
      )
      repoApi.apply(response.repository_status, response.commit_graph)
      setEditingFile(null)
    },
    [appendEntry, repoApi],
  )

  const historyUp = useCallback(() => {
    if (inputHistory.length === 0) return
    setHistoryIndex((idx) => {
      if (idx === null) {
        draftRef.current = inputValue
        const nextIdx = inputHistory.length - 1
        setInputValue(inputHistory[nextIdx])
        return nextIdx
      }
      const nextIdx = Math.max(0, idx - 1)
      setInputValue(inputHistory[nextIdx])
      return nextIdx
    })
  }, [inputHistory, inputValue])

  const historyDown = useCallback(() => {
    setHistoryIndex((idx) => {
      if (idx === null) return null
      const nextIdx = idx + 1
      if (nextIdx >= inputHistory.length) {
        setInputValue(draftRef.current)
        return null
      }
      setInputValue(inputHistory[nextIdx])
      return nextIdx
    })
  }, [inputHistory])

  const autocomplete = useCallback(
    (cursor: number) => completeInput(inputValue, cursor, graph.branches, knownPaths),
    [inputValue, graph.branches, knownPaths],
  )

  return {
    entries,
    inputValue,
    setInputValue,
    submit,
    historyUp,
    historyDown,
    autocomplete,
    isBusy: lifecycle.isBusy,
    phase: lifecycle.phase,
    editingFile,
    closeEditor,
    saveEditor,
  }
}
