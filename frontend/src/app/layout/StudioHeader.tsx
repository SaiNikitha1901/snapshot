import { navigate } from '../router'

/** Quiet continuation of the landing page's own header -- same
 * typographic language, not a traditional navbar. SNAPSHOT goes back
 * to the front door; STUDIO just names where you are. */
export function StudioHeader() {
  return (
    <header className="flex shrink-0 items-center justify-between border-b border-border bg-canvas px-4 py-2.5">
      <button
        type="button"
        onClick={() => navigate('/')}
        className="font-mono text-xs font-medium tracking-[0.2em] text-fg uppercase transition-colors hover:text-accent"
      >
        Snapshot
      </button>
      <span className="font-mono text-xs font-medium tracking-[0.2em] text-fg-subtle uppercase">Studio</span>
    </header>
  )
}
