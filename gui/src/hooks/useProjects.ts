import { useCallback, useEffect, useState } from 'react'

export interface Project {
  id: string
  name: string
  output_width: number
  output_height: number
  output_fps: number
  created_at: string
  updated_at: string
}

interface ProjectListResponse {
  projects: Project[]
  total: number
}

export interface Clip {
  id: string
  project_id: string
  source_video_id: string
  in_point: number
  out_point: number
  timeline_position: number
  created_at: string
  updated_at: string
}

interface ClipListResponse {
  clips: Clip[]
  total: number
}

interface UseProjectsOptions {
  page?: number
  pageSize?: number
}

interface UseProjectsResult {
  projects: Project[]
  total: number
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useProjects(options: UseProjectsOptions = {}): UseProjectsResult {
  const { page = 0, pageSize = 100 } = options
  const [projects, setProjects] = useState<Project[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [fetchKey, setFetchKey] = useState(0)

  const refetch = useCallback(() => setFetchKey((k) => k + 1), [])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)

    async function fetchProjects() {
      try {
        const params = new URLSearchParams({
          limit: String(pageSize),
          offset: String(page * pageSize),
        })
        const res = await fetch(`/api/v1/projects?${params}`)
        if (!res.ok) throw new Error(`Fetch failed: ${res.status}`)
        const json: ProjectListResponse = await res.json()
        if (active) {
          setProjects(json.projects)
          setTotal(json.total)
          setLoading(false)
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unknown error')
          setLoading(false)
        }
      }
    }

    fetchProjects()
    return () => {
      active = false
    }
  }, [page, pageSize, fetchKey])

  return { projects, total, loading, error, refetch }
}

export async function createProject(data: {
  name: string
  output_width: number
  output_height: number
  output_fps: number
}): Promise<Project> {
  const res = await fetch('/api/v1/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => null)
    throw new Error(detail?.detail?.message || `Create failed: ${res.status}`)
  }
  return res.json()
}

export async function deleteProject(id: string): Promise<void> {
  const res = await fetch(`/api/v1/projects/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    throw new Error(`Delete failed: ${res.status}`)
  }
}

export async function fetchClips(projectId: string): Promise<{ clips: Clip[]; total: number }> {
  const res = await fetch(`/api/v1/projects/${projectId}/clips`)
  if (!res.ok) throw new Error(`Fetch clips failed: ${res.status}`)
  const json: ClipListResponse = await res.json()
  return { clips: json.clips, total: json.total }
}
