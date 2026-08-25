import { HeroScene } from './landing/HeroScene'

/** The front door: a single interactive hero, nothing else. Static
 * and self-contained -- it never touches Studio state, context, or
 * the backend, so it works with nothing initialized. */
export function LandingPage() {
  return <HeroScene />
}
