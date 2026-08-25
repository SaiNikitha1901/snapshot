import { describe, expect, it } from 'vitest'
import type { ObjectGraph, ObjectGraphNode } from '../../types/snapshot'
import { buildObjectGraphLayout, type ObjectGraphNodeData } from './objectGraphLayout'

function makeNode(overrides: Partial<ObjectGraphNode> = {}): ObjectGraphNode {
  return {
    oid: 'a'.repeat(40),
    short_oid: 'aaaaaaa',
    kind: 'commit',
    label: 'first commit',
    depth: 0,
    lane: 0,
    is_head_commit: false,
    is_merge: null,
    ...overrides,
  }
}

describe('buildObjectGraphLayout', () => {
  it('maps depth and lane to x/y pixel coordinates', () => {
    const commit = makeNode({ oid: 'a'.repeat(40), depth: 0, lane: 0 })
    const tree = makeNode({ oid: 'b'.repeat(40), kind: 'tree', depth: 1, lane: 0, label: '1 entry' })
    const blob = makeNode({ oid: 'c'.repeat(40), kind: 'blob', depth: 2, lane: 0, label: '6 bytes' })
    const graph: ObjectGraph = {
      root_oid: commit.oid,
      nodes: [commit, tree, blob],
      edges: [
        { id: 'e1', source: commit.oid, target: tree.oid, label: 'tree' },
        { id: 'e2', source: tree.oid, target: blob.oid, label: 'a.txt' },
      ],
    }

    const { nodes, edges } = buildObjectGraphLayout(graph, null)

    const byOid = Object.fromEntries(nodes.map((n) => [n.id, n]))
    expect(byOid[commit.oid].position).toEqual({ x: 0, y: 0 })
    expect(byOid[tree.oid].position.x).toBeGreaterThan(byOid[commit.oid].position.x)
    expect(byOid[blob.oid].position.x).toBeGreaterThan(byOid[tree.oid].position.x)

    expect(edges).toHaveLength(2)
    expect(edges.find((e) => e.id === 'e2')?.label).toBe('a.txt')
  })

  it('spaces siblings at the same depth apart on the other axis', () => {
    const commit = makeNode({ oid: 'a'.repeat(40), depth: 0, lane: 0 })
    const treeA = makeNode({ oid: 'b'.repeat(40), kind: 'tree', depth: 1, lane: 0, label: '1 entry' })
    const treeB = makeNode({ oid: 'c'.repeat(40), kind: 'tree', depth: 1, lane: 1, label: '1 entry' })
    const graph: ObjectGraph = { root_oid: commit.oid, nodes: [commit, treeA, treeB], edges: [] }

    const { nodes } = buildObjectGraphLayout(graph, null)
    const byOid = Object.fromEntries(nodes.map((n) => [n.id, n]))

    expect(byOid[treeA.oid].position.x).toBe(byOid[treeB.oid].position.x) // same depth
    expect(byOid[treeA.oid].position.y).not.toBe(byOid[treeB.oid].position.y) // different lane
  })

  it('flags only the selected node as selected', () => {
    const commit = makeNode({ oid: 'a'.repeat(40) })
    const tree = makeNode({ oid: 'b'.repeat(40), kind: 'tree', depth: 1, label: '0 entries' })
    const graph: ObjectGraph = { root_oid: commit.oid, nodes: [commit, tree], edges: [] }

    const { nodes } = buildObjectGraphLayout(graph, tree.oid)
    const dataByOid = Object.fromEntries(nodes.map((n) => [n.id, n.data as ObjectGraphNodeData]))

    expect(dataByOid[commit.oid].isSelected).toBe(false)
    expect(dataByOid[tree.oid].isSelected).toBe(true)
  })

  it('passes edge labels through unchanged, including null for unlabeled edges', () => {
    const a = makeNode({ oid: 'a'.repeat(40) })
    const b = makeNode({ oid: 'b'.repeat(40), kind: 'tree', depth: 1, label: '0 entries' })
    const graph: ObjectGraph = {
      root_oid: a.oid,
      nodes: [a, b],
      edges: [{ id: 'e1', source: a.oid, target: b.oid, label: null }],
    }

    const { edges } = buildObjectGraphLayout(graph, null)
    expect(edges[0].label).toBeUndefined()
  })
})
