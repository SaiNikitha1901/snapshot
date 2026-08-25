import { useEffect } from 'react'
import { LearnPanel } from '../../features/learn/LearnPanel'
import { ObjectInspector } from '../../features/object-inspector/ObjectInspector'
import { RepositoryStatus } from '../../features/repository-status/RepositoryStatus'
import { Terminal } from '../../features/terminal/Terminal'
import { VisualizationPanel } from '../../features/visualization/VisualizationPanel'
import { useRepoApi } from '../../state/RepoStateContext'
import './StudioLayout.css'
import { Panel } from './Panel'
import { StudioHeader } from './StudioHeader'

export function StudioLayout() {
  const repoApi = useRepoApi()

  useEffect(() => {
    repoApi.hydrate()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount only
  }, [])

  return (
    <div className="snapshot-studio-shell animate-[fadein_0.3s_ease-out]">
      <StudioHeader />
      <div className="snapshot-studio-layout">
        <div className="snapshot-panel-viz">
          <VisualizationPanel />
        </div>

        <div className="snapshot-panel-side">
          <Panel title="Repository Status" className="max-h-[46%] shrink-0">
            <RepositoryStatus />
          </Panel>
          <Panel title="Object Inspector" className="flex-1">
            <ObjectInspector />
          </Panel>
        </div>

        <div className="snapshot-panel-term">
          <Panel title="Terminal" bodyClassName="flex flex-col">
            <Terminal />
          </Panel>
        </div>

        <div className="snapshot-panel-learn">
          <Panel title="Learn">
            <LearnPanel />
          </Panel>
        </div>
      </div>
    </div>
  )
}
