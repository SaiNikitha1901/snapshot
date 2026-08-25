import { render, screen } from '@testing-library/react'
import { useEffect } from 'react'
import { describe, expect, it } from 'vitest'
import { RepoStateProvider, useRepoApi } from '../../state/RepoStateContext'
import { SelectionProvider } from '../../state/SelectionContext'
import { makeStatus } from '../../test/fixtures'
import { RepositoryStatus } from './RepositoryStatus'

function Seed({ status }: { status: ReturnType<typeof makeStatus> }) {
  const api = useRepoApi()
  useEffect(() => {
    api.apply(status, { commits: [], branches: [], head_detached: false, head_commit_oid: null })
  }, [api, status])
  return null
}

function renderWithStatus(status: ReturnType<typeof makeStatus>) {
  return render(
    <RepoStateProvider>
      <SelectionProvider>
        <Seed status={status} />
        <RepositoryStatus />
      </SelectionProvider>
    </RepoStateProvider>,
  )
}

describe('RepositoryStatus', () => {
  it('prompts for init when the repository is not yet initialized', () => {
    render(
      <RepoStateProvider>
        <SelectionProvider>
          <RepositoryStatus />
        </SelectionProvider>
      </RepoStateProvider>,
    )
    expect(screen.getByText(/no repository yet/i)).toBeInTheDocument()
  })

  it('shows a clean, empty state', () => {
    renderWithStatus(makeStatus())
    expect(screen.getByText('clean')).toBeInTheDocument()
    expect(screen.getByText('empty')).toBeInTheDocument()
  })

  it('shows detached HEAD instead of a current branch', () => {
    renderWithStatus(makeStatus({ head_detached: true, current_branch: null }))
    expect(screen.getByText('detached')).toBeInTheDocument()
    expect(screen.getByText('— (detached)')).toBeInTheDocument()
  })

  it('lists conflicted paths distinctly from staged/modified ones', () => {
    renderWithStatus(
      makeStatus({
        working_directory_clean: false,
        staged_paths: ['a.txt'],
        unstaged_paths: [],
        conflicted_paths: ['b.txt'],
      }),
    )
    expect(screen.getByText('Conflicted (1)')).toBeInTheDocument()
    expect(screen.getByText('Staged (1)')).toBeInTheDocument()
    expect(screen.getByText('b.txt')).toBeInTheDocument()
  })
})
