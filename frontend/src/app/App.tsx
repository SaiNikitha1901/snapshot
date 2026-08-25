import { LandingPage } from '../pages/LandingPage'
import { StudioProviders } from '../state/StudioProviders'
import { StudioLayout } from './layout/StudioLayout'
import { usePathname } from './router'

export function App() {
  const pathname = usePathname()

  if (pathname === '/studio') {
    return (
      <StudioProviders>
        <StudioLayout />
      </StudioProviders>
    )
  }

  return <LandingPage />
}
