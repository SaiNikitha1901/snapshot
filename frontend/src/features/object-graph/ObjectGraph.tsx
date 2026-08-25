import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ReactFlow, { Controls, type Node, type NodeTypes, type ReactFlowInstance } from 'reactflow'
import 'reactflow/dist/style.css'
import { getObjectGraph } from '../../api/client'
import { useSelectionApi, useSelectionState } from '../../state/SelectionContext'
import type { ObjectGraph as ObjectGraphData } from '../../types/snapshot'
import { GraphFieldBackdrop } from '../commit-graph/GraphFieldBackdrop'
import './ObjectGraph.css'
import { buildObjectGraphLayout, type ObjectGraphNodeData } from './objectGraphLayout'
import { ObjectGraphNodeView } from './nodes/ObjectGraphNodeView'

const nodeTypes: NodeTypes = { object: ObjectGraphNodeView }

interface ObjectGraphProps {
  /** Which commit (or tree/blob) to root the graph at -- owned by
   * VisualizationPanel, which tracks the last-selected commit. */
  rootOid: string | null
}

function CenteredMessage({ tone, children }: { tone: 'muted' | 'danger'; children: React.ReactNode }) {
  return (
    <div className="relative h-full w-full">
      <GraphFieldBackdrop />
      <div
        className={`relative flex h-full w-full items-center justify-center p-6 text-center text-xs ${
          tone === 'danger' ? 'text-danger' : 'text-fg-subtle'
        }`}
      >
        {children}
      </div>
    </div>
  )
}

/** The object-level counterpart to CommitGraph: same React Flow setup,
 * same fitView-on-shape-change effect, same click -> selectByOid
 * wiring, same GraphFieldBackdrop. The one structural difference: this
 * data isn't part of every StudioResponse (most commands don't need
 * it), so it fetches for itself whenever `rootOid` changes. */
export function ObjectGraph({ rootOid }: ObjectGraphProps) {
  const [graph, setGraph] = useState<ObjectGraphData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { object: selected } = useSelectionState()
  const selectionApi = useSelectionApi()

  // This effect fetches from the network on rootOid change -- the
  // canonical "synchronize with an external system" use case, not a
  // value that could instead be derived during render. Every setState
  // below is either resetting for a new fetch or reporting that
  // fetch's outcome, so the whole body is exempted from
  // set-state-in-effect rather than chasing individual lines.
  /* eslint-disable react/set-state-in-effect */
  useEffect(() => {
    if (!rootOid) {
      setGraph(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    getObjectGraph(rootOid)
      .then((result) => {
        if (!cancelled) setGraph(result)
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load object graph')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [rootOid])
  /* eslint-enable react/set-state-in-effect */

  const selectedOid =
    selected && (selected.kind === 'commit' || selected.kind === 'blob' || selected.kind === 'tree')
      ? selected.oid
      : null
  const { nodes, edges } = useMemo(
    () => (graph ? buildObjectGraphLayout(graph, selectedOid) : { nodes: [], edges: [] }),
    [graph, selectedOid],
  )

  const instanceRef = useRef<ReactFlowInstance | null>(null)
  const handleInit = useCallback((instance: ReactFlowInstance) => {
    instanceRef.current = instance
  }, [])

  useEffect(() => {
    instanceRef.current?.fitView({ padding: 0.3, duration: 400 })
  }, [nodes.length, edges.length])

  const handleNodeClick = useCallback(
    (_: unknown, node: Node<ObjectGraphNodeData>) => {
      void selectionApi.selectByOid(node.data.node.oid)
    },
    [selectionApi],
  )

  if (!rootOid) {
    return (
      <CenteredMessage tone="muted">
        No commits yet. Run <span className="mx-1 font-mono text-fg">init</span>, stage a file, then{' '}
        <span className="mx-1 font-mono text-fg">commit</span> to see the object graph.
      </CenteredMessage>
    )
  }

  if (error) {
    return <CenteredMessage tone="danger">{error}</CenteredMessage>
  }

  if (loading || !graph) {
    return <CenteredMessage tone="muted">Loading…</CenteredMessage>
  }

  return (
    <div className="relative h-full w-full">
      <GraphFieldBackdrop />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onInit={handleInit}
        onNodeClick={handleNodeClick}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        panOnDrag
        zoomOnScroll
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
        maxZoom={2}
        className="!bg-transparent"
      >
        <Controls showInteractive={false} showZoom position="bottom-left" />
      </ReactFlow>
    </div>
  )
}
