import type { Edge, Node } from 'reactflow'
import type { CommitGraph, GraphBranchRef, GraphCommitNode } from '../../types/snapshot'

export interface CommitNodeData {
  kind: 'commit'
  commit: GraphCommitNode
  isSelected: boolean
}

export interface BranchRefNodeData {
  kind: 'branchRef'
  branch: GraphBranchRef
}

const COLUMN_WIDTH = 150
const ROW_HEIGHT = 96
const BRANCH_LABEL_OFFSET_Y = 48
const BRANCH_LABEL_STACK_STEP = 24

export function buildGraphLayout(
  graph: CommitGraph,
  selectedOid: string | null,
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []

  const positionByOid = new Map<string, { x: number; y: number }>()
  for (const commit of graph.commits) {
    const position = { x: commit.generation * COLUMN_WIDTH, y: commit.lane * ROW_HEIGHT }
    positionByOid.set(commit.oid, position)

    nodes.push({
      id: commit.oid,
      type: 'commit',
      position,
      draggable: false,
      connectable: false,
      data: { kind: 'commit', commit, isSelected: commit.oid === selectedOid } satisfies CommitNodeData,
    })

    if (commit.parent_oid) {
      edges.push({
        id: `${commit.parent_oid}->${commit.oid}`,
        source: commit.parent_oid,
        target: commit.oid,
        type: 'straight',
        style: { stroke: 'var(--color-border-strong)', strokeWidth: 1.5 },
      })
    }
    if (commit.merge_parent_oid) {
      edges.push({
        id: `${commit.merge_parent_oid}->${commit.oid}-merge`,
        source: commit.merge_parent_oid,
        target: commit.oid,
        type: 'straight',
        style: { stroke: 'var(--color-branch-blue)', strokeWidth: 1.5, strokeDasharray: '4 3' },
      })
    }
  }

  // Stack branch labels that share the same tip commit instead of overlapping them.
  const tipStackIndex = new Map<string, number>()
  for (const branch of graph.branches) {
    if (!branch.commit_oid) continue
    const tipPosition = positionByOid.get(branch.commit_oid)
    if (!tipPosition) continue

    const stackIndex = tipStackIndex.get(branch.commit_oid) ?? 0
    tipStackIndex.set(branch.commit_oid, stackIndex + 1)

    const labelId = `branch:${branch.name}`
    nodes.push({
      id: labelId,
      type: 'branchRef',
      position: { x: tipPosition.x, y: tipPosition.y - BRANCH_LABEL_OFFSET_Y - stackIndex * BRANCH_LABEL_STACK_STEP },
      draggable: false,
      connectable: false,
      data: { kind: 'branchRef', branch } satisfies BranchRefNodeData,
    })

    edges.push({
      id: `${labelId}->${branch.commit_oid}`,
      source: labelId,
      target: branch.commit_oid,
      type: 'straight',
      style: { stroke: 'var(--color-border-strong)', strokeWidth: 1, strokeDasharray: '2 3' },
    })
  }

  return { nodes, edges }
}
