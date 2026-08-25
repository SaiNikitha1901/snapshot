import { render, screen } from '@testing-library/react'
import { useEffect } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { LearnProvider, useLearnApi } from '../../state/LearnContext'
import { makeLearnCard } from '../../test/fixtures'
import type { LearnCard } from '../../types/snapshot'
import { LearnPanel } from './LearnPanel'

// setCards() fires a background enrichment request per card; these
// tests are about rendering the deterministic shape, so keep them
// isolated from the network rather than letting a real fetch() reject.
vi.mock('../../api/client', () => ({ generateLearnCard: vi.fn(() => new Promise(() => {})) }))

function Seed({ cards }: { cards: LearnCard[] }) {
  const api = useLearnApi()
  useEffect(() => {
    api.setCards(cards)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- seed once with the fixture cards
  }, [])
  return null
}

function renderWithCards(cards: LearnCard[]) {
  return render(
    <LearnProvider>
      <Seed cards={cards} />
      <LearnPanel />
    </LearnProvider>,
  )
}

describe('LearnPanel', () => {
  it('prompts the user to run a command when there are no cards yet', () => {
    render(
      <LearnProvider>
        <LearnPanel />
      </LearnProvider>,
    )
    expect(screen.getByText(/run a command in the terminal/i)).toBeInTheDocument()
  })

  it('renders Core Idea and Why for every card', () => {
    renderWithCards([makeLearnCard({ core_idea: 'The core idea.', why: 'The why.' })])
    expect(screen.getByText('Core Idea')).toBeInTheDocument()
    expect(screen.getByText('The core idea.')).toBeInTheDocument()
    expect(screen.getByText('Why')).toBeInTheDocument()
    expect(screen.getByText('The why.')).toBeInTheDocument()
  })

  it('omits the In Production Git section when not relevant', () => {
    renderWithCards([makeLearnCard({ in_production_git: null })])
    expect(screen.queryByText(/in production git/i)).not.toBeInTheDocument()
  })

  it('shows the In Production Git section only when present', () => {
    renderWithCards([makeLearnCard({ in_production_git: 'Real Git does X differently.' })])
    expect(screen.getByText(/in production git/i)).toBeInTheDocument()
    expect(screen.getByText('Real Git does X differently.')).toBeInTheDocument()
  })

  it('omits Explore Next when there is nothing to suggest', () => {
    renderWithCards([makeLearnCard({ explore_next: [] })])
    expect(screen.queryByText(/explore next/i)).not.toBeInTheDocument()
  })

  it('lists Explore Next suggestions when present', () => {
    renderWithCards([makeLearnCard({ explore_next: ['Try a merge conflict.'] })])
    expect(screen.getByText(/explore next/i)).toBeInTheDocument()
    expect(screen.getByText('Try a merge conflict.')).toBeInTheDocument()
  })
})
