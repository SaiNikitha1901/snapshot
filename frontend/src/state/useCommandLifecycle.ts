import { useCallback, useMemo, useState } from 'react'
import { runCommand } from '../api/client'
import type { CommandMeta, StudioResponse, TerminalOutput } from '../types/snapshot'
import { useAnimationApi } from './AnimationContext'
import { useLearnApi } from './LearnContext'
import { useRepoApi } from './RepoStateContext'
import { useSelectionApi } from './SelectionContext'

/**
 * Drives the exact command lifecycle the product spec fixes:
 * user input -> backend executes -> terminal prints output ->
 * visualization animates -> repository status updates -> learn
 * updates -> terminal interactive again. One `submit()` call walks
 * every phase in order for a single command.
 *
 * This hook does NOT own terminal scrollback -- the terminal feature
 * also has purely-local builtins (clear/history/help) that never
 * reach the backend, so it owns one combined, chronologically-ordered
 * list itself (see features/terminal/useTerminal.ts) rather than
 * merging two separate histories.
 */
export type LifecyclePhase = 'idle' | 'executing' | 'animating' | 'statusUpdating' | 'learnUpdating'

export interface CommandResult {
  ok: boolean
  command: CommandMeta
  terminal: TerminalOutput
}

export function useCommandLifecycle() {
  const [phase, setPhase] = useState<LifecyclePhase>('idle')
  const repoApi = useRepoApi()
  const selectionApi = useSelectionApi()
  const animationApi = useAnimationApi()
  const learnApi = useLearnApi()

  const submit = useCallback(
    async (input: string): Promise<CommandResult> => {
      setPhase('executing')

      let response: StudioResponse
      try {
        response = await runCommand(input)
      } catch (err) {
        setPhase('idle')
        return {
          ok: false,
          command: { raw_input: input, name: input.trim().split(/\s+/)[0] ?? '', args: [], recognized: false },
          terminal: {
            stdout_lines: [],
            stderr_lines: [
              err instanceof Error ? err.message : 'network error: could not reach the Snapshot Studio API',
            ],
            exit_code: 1,
          },
        }
      }

      if (response.animation && response.animation.steps.length > 0) {
        setPhase('animating')
        await animationApi.playSequence(response.animation)
      }

      setPhase('statusUpdating')
      repoApi.apply(response.repository_status, response.commit_graph)
      if (response.focused_object) {
        selectionApi.select(response.focused_object)
      }

      setPhase('learnUpdating')
      if (response.learn) {
        learnApi.setCards(response.learn.cards)
      }

      setPhase('idle')
      return { ok: true, command: response.command, terminal: response.terminal }
    },
    [animationApi, repoApi, selectionApi, learnApi],
  )

  return useMemo(() => ({ phase, submit, isBusy: phase !== 'idle' }), [phase, submit])
}
