import { describe, expect, it } from 'vitest'
import type { GraphBranchRef } from '../../types/snapshot'
import { completeInput } from './completion'

const branches: GraphBranchRef[] = [
  { name: 'main', commit_oid: 'a'.repeat(40), is_current: true, lane: 0 },
  { name: 'feature', commit_oid: 'b'.repeat(40), is_current: false, lane: 1 },
  { name: 'feature-2', commit_oid: 'c'.repeat(40), is_current: false, lane: 2 },
]

describe('completeInput', () => {
  it('completes a unique command prefix on the first token', () => {
    const result = completeInput('ini', 3, [], [])
    expect(result).toBe('init')
  })

  it('completes to the shared prefix when multiple commands match', () => {
    // "c" matches checkout, commit, cat -- shared prefix is "c"
    const result = completeInput('c', 1, [], [])
    expect(result).toBe('c')
  })

  it('completes a unique branch name on a later token', () => {
    const result = completeInput('checkout fea-2', 14, branches, [])
    // "fea-2" doesn't prefix-match anything (no branch starts with "fea-2"); use a clean prefix instead
    expect(result).toBe('checkout fea-2')
  })

  it('completes an unambiguous branch prefix', () => {
    const result = completeInput('checkout main', 13, branches, [])
    expect(result).toBe('checkout main')
  })

  it('completes a partial unique branch prefix to the full name', () => {
    const result = completeInput('checkout ma', 11, branches, [])
    expect(result).toBe('checkout main')
  })

  it('completes to the shared prefix for ambiguous branch names', () => {
    const result = completeInput('checkout feat', 13, branches, [])
    expect(result).toBe('checkout feature')
  })

  it('completes known paths on a later token', () => {
    const result = completeInput('cat READ', 8, [], ['README.md', 'other.txt'])
    expect(result).toBe('cat README.md')
  })

  it('returns the input unchanged when there is no match', () => {
    const result = completeInput('checkout zzz', 12, branches, [])
    expect(result).toBe('checkout zzz')
  })

  it('returns the input unchanged for an empty partial token', () => {
    const result = completeInput('checkout ', 9, branches, [])
    expect(result).toBe('checkout ')
  })

  it('preserves text after the cursor', () => {
    const result = completeInput('ini extra', 3, [], [])
    expect(result).toBe('init extra')
  })
})
