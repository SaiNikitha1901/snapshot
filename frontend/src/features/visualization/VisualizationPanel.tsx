import { useCallback, useState } from 'react'
import type { ObjectDetail } from '../../types/snapshot'
import { Panel } from '../../app/layout/Panel'
import { useRepoState } from '../../state/RepoStateContext'
import { useSelectionApi, useSelectionState } from '../../state/SelectionContext'
import { CommitGraph } from '../commit-graph/CommitGraph'
import { AnimationSpeedControl } from '../object-animation/AnimationSpeedControl'
import { AnimationStage } from '../object-animation/AnimationStage'
import { ObjectGraph } from '../object-graph/ObjectGraph'
import { ReflogView } from '../reflog/ReflogView'
import { ViewModeToggle, type ViewMode } from './ViewModeToggle'

/** Composes the three views inside the one Visualization Panel: the
 * Commit Graph, the Object Graph, and the Reflog list. Tracks which
 * commit the Object Graph is rooted at by watching the shared
 * selection rather than adding anything to CommitGraph.tsx -- clicking
 * a commit there (or a row in the Reflog view) already calls
 * selectByOid, so that's all it takes to "hand off" a commit to the
 * Objects tab. Defaults to HEAD until a commit has been explicitly
 * picked. */
export function VisualizationPanel() {
  const [mode, setMode] = useState<ViewMode>('commits')
  const { graph } = useRepoState()
  const { object: selected } = useSelectionState()
  const selectionApi = useSelectionApi()
  const [lastCommitOid, setLastCommitOid] = useState<string | null>(null)

  // "Adjust state during render" (React's own pattern for this,
  // rather than a useEffect): remember the last-selected commit's oid
  // as the selection changes, computed inline during render instead
  // of via an effect-triggered extra render pass.
  const [observedSelected, setObservedSelected] = useState<ObjectDetail | null>(selected)
  if (selected !== observedSelected) {
    setObservedSelected(selected)
    if (selected?.kind === 'commit') {
      setLastCommitOid(selected.oid)
    }
  }

  const objectGraphRoot = lastCommitOid ?? graph.head_commit_oid

  const handleViewInGraph = useCallback(
    (oid: string) => {
      void selectionApi.selectByOid(oid)
      setMode('objects')
    },
    [selectionApi],
  )

  return (
    <Panel
      title="Visualization"
      headerRight={
        <div className="flex items-center gap-3">
          <ViewModeToggle mode={mode} onChange={setMode} />
          <span className="h-3 w-px bg-border" aria-hidden="true" />
          <AnimationSpeedControl />
        </div>
      }
      bodyClassName="relative"
    >
      {mode === 'commits' && <CommitGraph />}
      {mode === 'objects' && <ObjectGraph rootOid={objectGraphRoot} />}
      {mode === 'reflog' && <ReflogView onViewInGraph={handleViewInGraph} />}
      <AnimationStage />
    </Panel>
  )
}
