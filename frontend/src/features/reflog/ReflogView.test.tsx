import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { SelectionProvider } from '../../state/SelectionContext'
import { makeReflogEntry } from '../../test/fixtures'
import type { ReflogEntry } from '../../types/snapshot'
import { ReflogView } from './ReflogView'

const { getReflogMock } = vi.hoisted(() => ({ getReflogMock: vi.fn() }))
vi.mock('../../api/client', () => ({ getReflog: getReflogMock, getObject: vi.fn() }))

function renderView(entries: ReflogEntry[], onViewInGraph = vi.fn()) {
  getReflogMock.mockResolvedValue({ entries })
  return render(
    <SelectionProvider>
      <ReflogView onViewInGraph={onViewInGraph} />
    </SelectionProvider>,
  )
}

describe('ReflogView', () => {
  it('shows an empty state before any HEAD movement has been recorded', async () => {
    renderView([])
    await waitFor(() => expect(screen.getByText(/no head movements recorded yet/i)).toBeInTheDocument())
  })

  it('renders one row per entry, newest first, with HEAD@{n}, short oid, and message', async () => {
    renderView([
      makeReflogEntry({ index: 0, new_oid: 'a'.repeat(40), short_new_oid: 'a'.repeat(7), message: 'checkout: moving from main to feature' }),
      makeReflogEntry({ index: 1, new_oid: 'b'.repeat(40), short_new_oid: 'b'.repeat(7), message: 'commit (initial): c1' }),
    ])
    await waitFor(() => expect(screen.getByText('a'.repeat(7))).toBeInTheDocument())
    expect(screen.getByText('HEAD@{0}')).toBeInTheDocument()
    expect(screen.getByText('checkout: moving from main to feature')).toBeInTheDocument()
    expect(screen.getByText('HEAD@{1}')).toBeInTheDocument()
    expect(screen.getByText('commit (initial): c1')).toBeInTheDocument()
  })

  it('shows the unreachable tag only when is_reachable is false', async () => {
    renderView([
      makeReflogEntry({ index: 0, new_oid: 'a'.repeat(40), is_reachable: true }),
      makeReflogEntry({ index: 1, new_oid: 'b'.repeat(40), is_reachable: false }),
    ])
    await waitFor(() => expect(screen.getAllByRole('button').length).toBeGreaterThan(0))
    expect(screen.getAllByText('unreachable')).toHaveLength(1)
  })

  it('clicking a row selects that commit by oid', async () => {
    const oid = 'a'.repeat(40)
    renderView([makeReflogEntry({ index: 0, new_oid: oid, short_new_oid: oid.slice(0, 7), message: 'commit (initial): c1' })])
    await waitFor(() => expect(screen.getByText('commit (initial): c1')).toBeInTheDocument())

    fireEvent.click(screen.getByText('commit (initial): c1'))

    const client = await import('../../api/client')
    await waitFor(() => expect(client.getObject).toHaveBeenCalledWith(oid))
  })

  it('clicking "View graph" invokes onViewInGraph with the entry oid, not the row selection', async () => {
    const onViewInGraph = vi.fn()
    const oid = 'a'.repeat(40)
    renderView([makeReflogEntry({ index: 0, new_oid: oid })], onViewInGraph)
    await waitFor(() => expect(screen.getByText('View graph')).toBeInTheDocument())

    fireEvent.click(screen.getByText('View graph'))

    expect(onViewInGraph).toHaveBeenCalledWith(oid)
  })
})
