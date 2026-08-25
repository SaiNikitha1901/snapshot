import type { GraphBranchRef } from '../../types/snapshot'
import { KNOWN_COMMAND_NAMES } from './builtinCommands'

function longestCommonPrefix(candidates: string[]): string {
  if (candidates.length === 0) return ''
  let prefix = candidates[0]
  for (const candidate of candidates.slice(1)) {
    let i = 0
    while (i < prefix.length && i < candidate.length && prefix[i] === candidate[i]) i += 1
    prefix = prefix.slice(0, i)
  }
  return prefix
}

/** Completes the token the cursor is currently in. Returns the full
 * input string with that token completed to the shared prefix of all
 * matches (or the single match, if there's exactly one). Returns the
 * input unchanged if there's no unambiguous completion. */
export function completeInput(
  input: string,
  cursor: number,
  branches: GraphBranchRef[],
  knownPaths: string[],
): string {
  const beforeCursor = input.slice(0, cursor)
  const afterCursor = input.slice(cursor)
  const tokenStart = beforeCursor.lastIndexOf(' ') + 1
  const partial = beforeCursor.slice(tokenStart)
  const isFirstToken = beforeCursor.slice(0, tokenStart).trim() === ''

  const pool = isFirstToken
    ? KNOWN_COMMAND_NAMES
    : [...branches.map((b) => b.name), ...knownPaths]

  const matches = pool.filter((candidate) => candidate.startsWith(partial) && partial.length > 0)
  if (matches.length === 0) return input

  const completion = matches.length === 1 ? matches[0] : longestCommonPrefix(matches)
  if (completion.length <= partial.length) return input

  return beforeCursor.slice(0, tokenStart) + completion + afterCursor
}
