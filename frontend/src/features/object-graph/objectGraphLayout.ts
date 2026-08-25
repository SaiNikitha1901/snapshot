import type { Edge, Node } from 'reactflow'
import type { ObjectGraph, ObjectGraphNode } from '../../types/snapshot'

export interface ObjectGraphNodeData {
  node: ObjectGraphNode
  isSelected: boolean
}

// Same coordinate approach as commit-graph/graphLayout.ts: the backend
// owns depth/lane, this only maps them to pixels. depth->x mirrors the
// commit graph's own generation->x convention (left to right), so
// switching between the two views doesn't feel like a different
// paradigm.
const COLUMN_WIDTH = 170
const ROW_HEIGHT = 90

export function buildObjectGraphLayout(graph: ObjectGraph, selectedOid: string | null): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = graph.nodes.map((node) => ({
    id: node.oid,
    type: 'object',
    position: { x: node.depth * COLUMN_WIDTH, y: node.lane * ROW_HEIGHT },
    draggable: false,
    connectable: false,
    data: { node, isSelected: node.oid === selectedOid } satisfies ObjectGraphNodeData,
  }))

  const edges: Edge[] = graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'straight',
    label: edge.label ?? undefined,
    style: { stroke: 'var(--color-border-strong)', strokeWidth: 1.5 },
  }))

  return { nodes, edges }
}
