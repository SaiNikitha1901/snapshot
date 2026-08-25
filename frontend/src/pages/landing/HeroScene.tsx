import { useRef, useState } from 'react'
import { navigate } from '../../app/router'
import { FAR_FIELD, NEAR_FIELD, PULSE_EDGES, VIEW_HEIGHT, VIEW_WIDTH, type FieldLayer } from '../../shared/gitField'
import './HeroScene.css'
import { useCursorParallax } from './useCursorParallax'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

interface FieldSvgProps {
  layer: FieldLayer
  interactive?: boolean
  showPulses?: boolean
  hoveredId: string | null
  onHover: (id: string | null) => void
}

/** One depth layer of the field: thin connector lines, small nodes
 * that drift on their own via CSS, and (near layer only) a hover
 * reveal of the node's hash plus a couple of accent pulses traveling
 * along edges via native SVG animateMotion -- no JS animation loop
 * needed for that part. Purely decorative -- aria-hidden at the
 * caller. */
function FieldSvg({ layer, interactive, showPulses, hoveredId, onHover }: FieldSvgProps) {
  return (
    <svg
      className="h-full w-full"
      viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
      preserveAspectRatio="xMidYMid slice"
    >
      {layer.edges.map((edge) => (
        <line key={edge.id} x1={edge.x1} y1={edge.y1} x2={edge.x2} y2={edge.y2} className="field-edge" />
      ))}

      {showPulses &&
        PULSE_EDGES.map((edge, i) => (
          <circle key={`pulse-${edge.id}`} r={3} className="field-pulse">
            <animateMotion
              dur={`${7 + i * 2}s`}
              repeatCount="indefinite"
              begin={`${i * 1.6}s`}
              path={`M${edge.x1},${edge.y1} L${edge.x2},${edge.y2}`}
            />
          </circle>
        ))}

      {layer.nodes.map((node) => (
        <g
          key={node.id}
          className="field-node-drift"
          style={{ animationDelay: `${node.driftDelay}s`, animationDuration: `${node.driftDuration}s` }}
        >
          <circle
            cx={node.x}
            cy={node.y}
            r={interactive ? 3.5 : 2.5}
            className={`field-node ${interactive ? 'field-node-interactive' : ''} ${
              hoveredId === node.id ? 'field-node-active' : ''
            }`}
            onPointerEnter={interactive ? () => onHover(node.id) : undefined}
            onPointerLeave={interactive ? () => onHover(null) : undefined}
          />
          {interactive && (
            <text
              x={node.x + 8}
              y={node.y - 8}
              className={`field-label ${hoveredId === node.id ? 'field-label-visible' : ''}`}
            >
              {node.hash}
            </text>
          )}
        </g>
      ))}
    </svg>
  )
}

/** The entire landing page: one interactive hero. Two depth layers of
 * Git-native "material" (nodes, hashes, connector lines) drift toward
 * the cursor at different speeds behind large, confident typography,
 * which gets its own faint counter-drift so the whole scene reads as
 * one dimensional object rather than a flat page. */
export function HeroScene() {
  const farRef = useRef<HTMLDivElement>(null)
  const typeRef = useRef<HTMLDivElement>(null)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const reducedMotion = usePrefersReducedMotion()

  // Only the decorative far layer (and a faint counter-drift on the
  // type) tracks the cursor. The near layer is where the hoverable
  // nodes live -- if it also chased the cursor, a node would drift
  // out from under the pointer as it approaches, fighting the very
  // hover it's meant to reveal. Keeping it positionally stable (its
  // own slow autonomous per-node drift is still running) makes the
  // hover-reveal reliable while still reading as a distinct depth
  // plane from the far layer, like a shallow depth of field.
  useCursorParallax([
    { ref: farRef, factor: 16 },
    { ref: typeRef, factor: -6 },
  ])

  return (
    <div className="relative min-h-screen overflow-hidden bg-canvas">
      <div ref={farRef} className="pointer-events-none absolute inset-0" aria-hidden="true">
        <FieldSvg layer={FAR_FIELD} hoveredId={null} onHover={() => {}} />
      </div>
      <div className="absolute inset-0" aria-hidden="true">
        <FieldSvg
          layer={NEAR_FIELD}
          interactive
          showPulses={!reducedMotion}
          hoveredId={hoveredId}
          onHover={setHoveredId}
        />
      </div>

      {/* min-h-screen is needed for flex centering, but that means this
          wrapper's (mostly invisible) box spans the whole viewport --
          without pointer-events-none it would silently block every
          hover/click reaching the field layers underneath it. Only the
          button opts back in. */}
      <div className="pointer-events-none relative z-10 flex min-h-screen flex-col items-center justify-center px-8 text-center">
        <div ref={typeRef} className="flex flex-col items-center gap-6">
          <span className="font-mono text-xs font-medium tracking-[0.3em] text-fg-subtle uppercase">Snapshot</span>
          <h1 className="font-sans text-[clamp(2.75rem,8vw,6.25rem)] leading-[0.95] font-semibold tracking-tight text-fg">
            WATCH GIT
            <br />
            <span className="text-accent">THINK.</span>
          </h1>
          <p className="max-w-[42ch] text-base text-fg-muted sm:text-lg">
            An educational version control system built from scratch to make Git's internals visible.
          </p>
          <button
            type="button"
            onClick={() => navigate('/studio')}
            className="group pointer-events-auto mt-4 flex items-center gap-2 rounded-md border border-accent bg-accent-soft px-5 py-2.5 font-mono text-sm tracking-wide text-accent uppercase transition-colors hover:bg-accent hover:text-accent-fg"
          >
            Use Snapshot
            <span className="transition-transform group-hover:translate-x-1" aria-hidden="true">
              →
            </span>
          </button>
        </div>
      </div>
    </div>
  )
}
