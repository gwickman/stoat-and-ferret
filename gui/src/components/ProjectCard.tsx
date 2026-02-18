import type { Project } from '../hooks/useProjects'

interface ProjectCardProps {
  project: Project
  clipCount: number
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}

function formatDate(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function ProjectCard({ project, clipCount, onSelect, onDelete }: ProjectCardProps) {
  return (
    <div
      className="rounded-lg border border-gray-700 bg-gray-800 p-4 transition-colors hover:border-gray-500"
      data-testid={`project-card-${project.id}`}
    >
      <div className="mb-2 flex items-start justify-between">
        <button
          onClick={() => onSelect(project.id)}
          className="text-left text-lg font-medium text-gray-200 hover:text-white"
          data-testid={`project-name-${project.id}`}
        >
          {project.name}
        </button>
        <button
          onClick={() => onDelete(project.id)}
          className="rounded px-2 py-1 text-xs text-red-400 hover:bg-red-900/30 hover:text-red-300"
          data-testid={`project-delete-${project.id}`}
          aria-label={`Delete ${project.name}`}
        >
          Delete
        </button>
      </div>
      <div className="space-y-1 text-sm text-gray-400">
        <p data-testid={`project-date-${project.id}`}>Created {formatDate(project.created_at)}</p>
        <p data-testid={`project-clips-${project.id}`}>{clipCount} clip{clipCount !== 1 ? 's' : ''}</p>
        <p className="text-xs text-gray-400">
          {project.output_width}x{project.output_height} @ {project.output_fps}fps
        </p>
      </div>
    </div>
  )
}
