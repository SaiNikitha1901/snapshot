/**
 * Deterministic, seeded "visual material" evoking Git's object graph
 * -- small nodes and thin connector lines, not an actual diagram.
 * Computed once at module load (no runtime randomness, no per-render
 * cost). Shared between the landing page's hero (two layers, for
 * independent parallax speeds) and the Studio's commit graph backdrop
 * (a single faint static layer), so the same visual language actually
 * carries from one into the other.
 */

export interface FieldNode {
  id: string
  x: number
  y: number
  hash: string
  driftDelay: number
  driftDuration: number
}

export interface FieldEdge {
  id: string
  x1: number
  y1: number
  x2: number
  y2: number
}

export interface FieldLayer {
  nodes: FieldNode[]
  edges: FieldEdge[]
}

export const VIEW_WIDTH = 1600
export const VIEW_HEIGHT = 1000

// Roughly where the hero typography sits -- kept sparse so the field
// reads as material around the type, not clutter behind it.
const SAFE_ZONE = { x1: 480, y1: 240, x2: 1120, y2: 700 }

function createRng(seed: number): () => number {
  let state = seed
  return () => {
    state = (state * 1103515245 + 12345) % 2147483648
    return state / 2147483648
  }
}

function insideSafeZone(x: number, y: number): boolean {
  return x > SAFE_ZONE.x1 && x < SAFE_ZONE.x2 && y > SAFE_ZONE.y1 && y < SAFE_ZONE.y2
}

function randomHash(rng: () => number, length = 7): string {
  const digits = '0123456789abcdef'
  let result = ''
  for (let i = 0; i < length; i += 1) {
    result += digits[Math.floor(rng() * digits.length)]
  }
  return result
}

function generateNodes(rng: () => number, count: number, prefix: string): FieldNode[] {
  const nodes: FieldNode[] = []
  let attempts = 0
  while (nodes.length < count && attempts < count * 25) {
    attempts += 1
    const x = rng() * VIEW_WIDTH
    const y = rng() * VIEW_HEIGHT
    if (insideSafeZone(x, y)) continue
    nodes.push({
      id: `${prefix}-${nodes.length}`,
      x,
      y,
      hash: randomHash(rng),
      driftDelay: rng() * 6,
      driftDuration: 7 + rng() * 5,
    })
  }
  return nodes
}

function generateEdges(rng: () => number, nodes: FieldNode[], connectChance: number, prefix: string): FieldEdge[] {
  const edges: FieldEdge[] = []
  for (let i = 1; i < nodes.length; i += 1) {
    if (rng() > connectChance) continue
    // Connect to a recent-ish earlier node so lines stay short and
    // local -- a loose scatter of connections, not a starburst.
    const backIndex = Math.max(0, i - 1 - Math.floor(rng() * 3))
    const a = nodes[i]
    const b = nodes[backIndex]
    edges.push({ id: `${prefix}-${edges.length}`, x1: a.x, y1: a.y, x2: b.x, y2: b.y })
  }
  return edges
}

const farRng = createRng(1337)
const farNodes = generateNodes(farRng, 13, 'far')
const farEdges = generateEdges(farRng, farNodes, 0.4, 'far-edge')

const nearRng = createRng(7331)
const nearNodes = generateNodes(nearRng, 9, 'near')
const nearEdges = generateEdges(nearRng, nearNodes, 0.55, 'near-edge')

export const FAR_FIELD: FieldLayer = { nodes: farNodes, edges: farEdges }
export const NEAR_FIELD: FieldLayer = { nodes: nearNodes, edges: nearEdges }

/** A couple of near-layer edges host a small accent pulse traveling
 * along them, on their own timers -- "the orange accent travels
 * through parts of the system." */
export const PULSE_EDGES: FieldEdge[] = nearEdges.slice(0, 2)
