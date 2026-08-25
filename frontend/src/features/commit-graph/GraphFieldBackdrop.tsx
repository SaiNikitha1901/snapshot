import { FAR_FIELD, VIEW_HEIGHT, VIEW_WIDTH } from '../../shared/gitField'

/** The same Git-object "visual material" from the landing page's
 * hero, reduced to a faint static line layer behind the commit graph
 * -- edges only, no nodes/labels/motion, so it reads as ambient
 * texture ("the Git object space") rather than competing with the
 * real commits React Flow renders on top of it. This is what carries
 * the landing page's visual language into the Studio, replacing
 * React Flow's default dot-grid Background (the most recognizable
 * "generic React Flow demo" signature). */
export function GraphFieldBackdrop() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.12]"
      viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      {FAR_FIELD.edges.map((edge) => (
        <line
          key={edge.id}
          x1={edge.x1}
          y1={edge.y1}
          x2={edge.x2}
          y2={edge.y2}
          stroke="var(--color-border-strong)"
          strokeWidth={1}
        />
      ))}
    </svg>
  )
}
