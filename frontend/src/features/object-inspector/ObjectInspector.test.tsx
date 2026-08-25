import { render, screen } from '@testing-library/react'
import { useEffect } from 'react'
import { describe, expect, it } from 'vitest'
import { SelectionProvider, useSelectionApi } from '../../state/SelectionContext'
import type { ObjectDetail } from '../../types/snapshot'
import { ObjectInspector } from './ObjectInspector'

function Seed({ object }: { object: ObjectDetail }) {
  const api = useSelectionApi()
  useEffect(() => {
    api.select(object)
  }, [api, object])
  return null
}

function renderWithObject(object: ObjectDetail) {
  return render(
    <SelectionProvider>
      <Seed object={object} />
      <ObjectInspector />
    </SelectionProvider>,
  )
}

describe('ObjectInspector', () => {
  it('shows an empty state with a way to jump to HEAD when nothing is selected', () => {
    render(
      <SelectionProvider>
        <ObjectInspector />
      </SelectionProvider>,
    )
    expect(screen.getByText(/nothing selected/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'View HEAD' })).toBeInTheDocument()
  })

  it('renders a blob object with its content', () => {
    renderWithObject({ kind: 'blob', oid: 'a'.repeat(40), size: 5, content: 'hi\n', is_binary: false })
    expect(screen.getByText('hi')).toBeInTheDocument()
  })

  it('renders a binary blob without dumping its bytes', () => {
    renderWithObject({ kind: 'blob', oid: 'a'.repeat(40), size: 100, content: null, is_binary: true })
    expect(screen.getByText(/binary content, not shown/i)).toBeInTheDocument()
  })

  it('renders a tree object listing its entries', () => {
    renderWithObject({
      kind: 'tree',
      oid: 'a'.repeat(40),
      entries: [{ mode: '100644', name: 'README.md', oid: 'b'.repeat(40), type: 'blob' }],
    })
    expect(screen.getByText('README.md')).toBeInTheDocument()
    expect(screen.getByText((_, node) => node?.textContent?.trim() === 'tree aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa · 1 entry')).toBeInTheDocument()
  })

  it('renders a merge commit with both parents', () => {
    renderWithObject({
      kind: 'commit',
      oid: 'a'.repeat(40),
      tree_oid: 'b'.repeat(40),
      parent_oid: 'c'.repeat(40),
      merge_parent_oid: 'd'.repeat(40),
      author: 'Snapshot User <snapshot@example.com> 1',
      committer: 'Snapshot User <snapshot@example.com> 1',
      message: 'Merge feature into main',
      is_merge: true,
    })
    expect(screen.getByText('merge')).toBeInTheDocument()
    expect(screen.getByText('merge parent')).toBeInTheDocument()
  })

  it('renders a first commit with no parent', () => {
    renderWithObject({
      kind: 'commit',
      oid: 'a'.repeat(40),
      tree_oid: 'b'.repeat(40),
      parent_oid: null,
      merge_parent_oid: null,
      author: 'Snapshot User <snapshot@example.com> 1',
      committer: 'Snapshot User <snapshot@example.com> 1',
      message: 'first commit',
      is_merge: false,
    })
    expect(screen.getByText(/first commit\)/)).toBeInTheDocument()
  })

  it('renders detached HEAD distinctly from symbolic HEAD', () => {
    renderWithObject({ kind: 'head', detached: true, branch_name: null, commit_oid: 'a'.repeat(40) })
    expect(screen.getByText('detached')).toBeInTheDocument()
  })
})
