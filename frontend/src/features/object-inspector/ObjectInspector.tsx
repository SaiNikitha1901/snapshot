import { useSelectionApi, useSelectionState } from '../../state/SelectionContext'
import { BlobView } from './BlobView'
import { BranchView } from './BranchView'
import { CommitView } from './CommitView'
import { HeadView } from './HeadView'
import { TreeView } from './TreeView'

export function ObjectInspector() {
  const { object, loading, error } = useSelectionState()
  const selectionApi = useSelectionApi()

  if (loading) {
    return <div className="p-4 text-xs text-fg-subtle">Loading…</div>
  }

  if (error) {
    return <div className="p-4 text-xs text-danger">{error}</div>
  }

  if (!object) {
    return (
      <div className="flex flex-col items-start gap-2 p-4 text-xs text-fg-subtle">
        <p>Nothing selected. Click a commit in the graph, or an object it links to, to inspect it here.</p>
        <button type="button" className="text-accent hover:underline" onClick={() => void selectionApi.selectHead()}>
          View HEAD
        </button>
      </div>
    )
  }

  switch (object.kind) {
    case 'blob':
      return <BlobView object={object} />
    case 'tree':
      return <TreeView object={object} />
    case 'commit':
      return <CommitView object={object} />
    case 'branch':
      return <BranchView object={object} />
    case 'head':
      return <HeadView object={object} />
  }
}
