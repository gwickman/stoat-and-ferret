import type { Project } from '../hooks/useProjects'
import ProjectCard from './ProjectCard'

interface ProjectListProps {
  projects: Project[]
  clipCounts: Record<string, number>
  loading: boolean
  error: string | null
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}

export default function ProjectList({
  projects,
  clipCounts,
  loading,
  error,
  onSelect,
  onDelete,
}: ProjectListProps) {
  if (loading) {
    return (
      <div className="py-12 text-center text-gray-400" data-testid="project-list-loading">
        Loading projects...
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-12 text-center text-red-400" data-testid="project-list-error">
        {error}
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="py-12 text-center text-gray-400" data-testid="project-list-empty">
        No projects yet. Create one to get started.
      </div>
    )
  }

  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
      data-testid="project-list"
    >
      {projects.map((project) => (
        <ProjectCard
          key={project.id}
          project={project}
          clipCount={clipCounts[project.id] ?? 0}
          onSelect={onSelect}
          onDelete={onDelete}
        />
      ))}
    </div>
  )
}
