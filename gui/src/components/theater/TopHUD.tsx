import { useProjectStore } from '../../stores/projectStore'
import { useProjects } from '../../hooks/useProjects'
import AIActionIndicator from './AIActionIndicator'

/**
 * Top HUD overlay for Theater Mode.
 *
 * Displays the current project title and AI action indicator.
 * Positioned at the top of the fullscreen container with a
 * gradient background for readability over video content.
 */
export default function TopHUD() {
  const selectedProjectId = useProjectStore((s) => s.selectedProjectId)
  const { projects } = useProjects()
  const project = projects.find((p) => p.id === selectedProjectId)

  return (
    <div
      data-testid="theater-top-hud"
      className="pointer-events-auto absolute top-0 right-0 left-0 flex items-center gap-3 bg-gradient-to-b from-black/70 to-transparent px-4 py-3"
    >
      <span className="text-sm font-medium text-white">
        {project?.name ?? 'Untitled Project'}
      </span>
      <AIActionIndicator />
    </div>
  )
}
