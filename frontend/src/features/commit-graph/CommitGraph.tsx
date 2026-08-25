import { useCallback, useEffect, useMemo, useRef } from 'react'
import ReactFlow, { Controls, type Node, type NodeTypes, type ReactFlowInstance } from 'reactflow'
import 'reactflow/dist/style.css'
import { useRepoState } from '../../state/RepoStateContext'
import { useSelectionApi, useSelectionState } from '../../state/SelectionContext'
import './CommitGraph.css'
import { GraphFieldBackdrop } from './GraphFieldBackdrop'
import { buildGraphLayout, type BranchRefNodeData, type CommitNodeData } from './graphLayout'
import { BranchRefNode } from './nodes/BranchRefNode'
import { CommitNode } from './nodes/CommitNode'

const nodeTypes: NodeTypes = { commit: CommitNode, branchRef: BranchRefNode }

export function CommitGraph() {
  const { graph } = useRepoState()
  const { object: selected } = useSelectionState()
  const selectionApi = useSelectionApi()

  const selectedOid = selected && (selected.kind === 'commit' || selected.kind === 'blob' || selected.kind === 'tree') ? selected.oid : null
  const { nodes, edges } = useMemo(() => buildGraphLayout(graph, selectedOid), [graph, selectedOid])

  const instanceRef = useRef<ReactFlowInstance | null>(null)
  const handleInit = useCallback((instance: ReactFlowInstance) => {
    instanceRef.current = instance
  }, [])

  // `fitView` (the prop) only fits once, on mount. Re-fit whenever the
  // graph's *shape* changes (new commits/branches) -- not on every
  // render, so a click-to-select doesn't yank the viewport around.
  useEffect(() => {
    instanceRef.current?.fitView({ padding: 0.3, duration: 400 })
  }, [nodes.length, edges.length])

  const handleNodeClick = useCallback(
    (_: unknown, node: Node<CommitNodeData | BranchRefNodeData>) => {
      if (node.data.kind === 'commit') {
        void selectionApi.selectByOid(node.data.commit.oid)
      } else {
        void selectionApi.selectBranch(node.data.branch.name)
      }
    },
    [selectionApi],
  )

  if (graph.commits.length === 0) {
    return (
      <div className="relative h-full w-full">
        <GraphFieldBackdrop />
        <div className="relative flex h-full w-full items-center justify-center p-6 text-center text-xs text-fg-subtle">
          No commits yet. Run <span className="mx-1 font-mono text-fg">init</span>, stage a file, then{' '}
          <span className="mx-1 font-mono text-fg">commit</span> to see the graph.
        </div>
      </div>
    )
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
