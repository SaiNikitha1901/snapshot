import { useSyncExternalStore } from 'react'

/**
 * Snapshot has exactly two destinations -- the landing page at `/` and
 * the Studio at `/studio` -- so this is a deliberately minimal
 * path-based router rather than a routing library dependency. Browser
 * back/forward (`popstate`) and programmatic `navigate()` both funnel
 * through the same subscriber set via `useSyncExternalStore`.
 */

const listeners = new Set<() => void>()

function getSnapshot(): string {
  return window.location.pathname
}

function subscribe(listener: () => void): () => void {
  window.addEventListener('popstate', listener)
  listeners.add(listener)
  return () => {
    window.removeEventListener('popstate', listener)
    listeners.delete(listener)
  }
}

export function navigate(path: string): void {
  if (window.location.pathname === path) return
  window.history.pushState({}, '', path)
  listeners.forEach((listener) => listener())
}

export function usePathname(): string {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
}
