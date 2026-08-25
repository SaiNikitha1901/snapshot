import { useEffect } from 'react'
import type { RefObject } from 'react'

interface ParallaxLayer {
  ref: RefObject<HTMLElement | null>
  /** Roughly the pixel offset at full cursor travel to one edge of the viewport. */
  factor: number
}

/**
 * Cursor-driven depth: one shared pointermove listener and one shared
 * requestAnimationFrame loop drive every layer, each at its own
 * factor, so the scene reads as layers moving at different depths
 * rather than one flat plane. Applies transforms directly via refs
 * (no React state in the hot path) so this never triggers a
 * re-render -- cheap enough to run every frame.
 */
export function useCursorParallax(layers: ParallaxLayer[]): void {
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const target = { x: 0, y: 0 }
    const current = { x: 0, y: 0 }

    function handlePointerMove(event: PointerEvent) {
      target.x = (event.clientX / window.innerWidth) * 2 - 1
      target.y = (event.clientY / window.innerHeight) * 2 - 1
    }
    window.addEventListener('pointermove', handlePointerMove)

    let frameId: number
    function tick() {
      current.x += (target.x - current.x) * 0.06
      current.y += (target.y - current.y) * 0.06
      for (const layer of layers) {
        const el = layer.ref.current
        if (el) {
          const x = (current.x * layer.factor).toFixed(2)
          const y = (current.y * layer.factor).toFixed(2)
          el.style.transform = `translate3d(${x}px, ${y}px, 0)`
        }
      }
      frameId = requestAnimationFrame(tick)
    }
    frameId = requestAnimationFrame(tick)

    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      cancelAnimationFrame(frameId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- layer refs are stable for the component's lifetime
  }, [])
}
