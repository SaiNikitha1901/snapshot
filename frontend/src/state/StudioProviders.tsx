import type { ReactNode } from 'react'
import { AnimationProvider } from './AnimationContext'
import { LearnProvider } from './LearnContext'
import { RepoStateProvider } from './RepoStateContext'
import { SelectionProvider } from './SelectionContext'

export function StudioProviders({ children }: { children: ReactNode }) {
  return (
    <RepoStateProvider>
      <SelectionProvider>
        <AnimationProvider>
          <LearnProvider>{children}</LearnProvider>
        </AnimationProvider>
      </SelectionProvider>
    </RepoStateProvider>
  )
}
