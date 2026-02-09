import { useCallback, useEffect, useState } from 'react'
import CreateProjectModal from '../components/CreateProjectModal'
import DeleteConfirmation from '../components/DeleteConfirmation'
import ProjectDetails from '../components/ProjectDetails'
import ProjectList from '../components/ProjectList'
import { type Project, fetchClips, useProjects } from '../hooks/useProjects'
import { useProjectStore } from '../stores/projectStore'

export default function ProjectsPage() {
  const { projects, loading, error, refetch } = useProjects()
  const {
    selectedProjectId,
    createModalOpen,
    deleteModalOpen,
    setSelectedProjectId,
    setCreateModalOpen,
    setDeleteModalOpen,
  } = useProjectStore()

  const [clipCounts, setClipCounts] = useState<Record<string, number>>({})
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null)

  // Fetch clip counts for all projects
  useEffect(() => {
    if (projects.length === 0) return

    let active = true
    async function loadCounts() {
      const counts: Record<string, number> = {}
      await Promise.all(
        projects.map(async (p) => {
          try {
            const result = await fetchClips(p.id)
            counts[p.id] = result.total
          } catch {
            counts[p.id] = 0
          }
        }),
      )
      if (active) setClipCounts(counts)
    }

    loadCounts()
    return () => {
      active = false
    }
  }, [projects])

  const selectedProject: Project | undefined = projects.find(
    (p) => p.id === selectedProjectId,
  )

  const handleSelect = useCallback(
    (id: string) => setSelectedProjectId(id),
    [setSelectedProjectId],
  )

  const handleDelete = useCallback(
    (id: string) => {
      setDeleteTargetId(id)
      setDeleteModalOpen(true)
    },
    [setDeleteModalOpen],
  )

  const handleDeleted = useCallback(() => {
    if (deleteTargetId === selectedProjectId) {
      setSelectedProjectId(null)
    }
    setDeleteTargetId(null)
    refetch()
  }, [deleteTargetId, selectedProjectId, setSelectedProjectId, refetch])

  const handleCreated = useCallback(() => {
    refetch()
  }, [refetch])

  const deleteTarget = projects.find((p) => p.id === deleteTargetId)

  return (
    <div className="p-6" data-testid="projects-page">
      {selectedProject ? (
        <ProjectDetails
          project={selectedProject}
          onBack={() => setSelectedProjectId(null)}
          onDelete={handleDelete}
        />
      ) : (
        <>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-2xl font-semibold">Projects</h2>
            <button
              onClick={() => setCreateModalOpen(true)}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
              data-testid="btn-new-project"
            >
              New Project
            </button>
          </div>

          <ProjectList
            projects={projects}
            clipCounts={clipCounts}
            loading={loading}
            error={error}
            onSelect={handleSelect}
            onDelete={handleDelete}
          />
        </>
      )}

      <CreateProjectModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onCreated={handleCreated}
      />

      <DeleteConfirmation
        open={deleteModalOpen}
        projectId={deleteTarget?.id ?? ''}
        projectName={deleteTarget?.name ?? ''}
        onClose={() => {
          setDeleteModalOpen(false)
          setDeleteTargetId(null)
        }}
        onDeleted={handleDeleted}
      />
    </div>
  )
}
