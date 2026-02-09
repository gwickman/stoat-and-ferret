import { useCallback, useEffect, useState } from 'react'
import type { SortField, SortOrder } from '../stores/libraryStore'

export interface Video {
  id: string
  path: string
  filename: string
  duration_frames: number
  frame_rate_numerator: number
  frame_rate_denominator: number
  width: number
  height: number
  video_codec: string
  audio_codec: string | null
  file_size: number
  thumbnail_path: string | null
  created_at: string
  updated_at: string
}

interface VideoListResponse {
  videos: Video[]
  total: number
  limit: number
  offset: number
}

interface VideoSearchResponse {
  videos: Video[]
  total: number
  query: string
}

interface UseVideosOptions {
  searchQuery: string
  sortField: SortField
  sortOrder: SortOrder
  page: number
  pageSize: number
}

interface UseVideosResult {
  videos: Video[]
  total: number
  loading: boolean
  error: string | null
  refetch: () => void
}

function sortVideos(
  videos: Video[],
  field: SortField,
  order: SortOrder,
): Video[] {
  const sorted = [...videos].sort((a, b) => {
    switch (field) {
      case 'name':
        return a.filename.localeCompare(b.filename)
      case 'duration': {
        const durA =
          a.frame_rate_denominator > 0
            ? a.duration_frames / (a.frame_rate_numerator / a.frame_rate_denominator)
            : 0
        const durB =
          b.frame_rate_denominator > 0
            ? b.duration_frames / (b.frame_rate_numerator / b.frame_rate_denominator)
            : 0
        return durA - durB
      }
      case 'date':
      default:
        return (
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        )
    }
  })
  return order === 'desc' ? sorted.reverse() : sorted
}

export function useVideos(options: UseVideosOptions): UseVideosResult {
  const { searchQuery, sortField, sortOrder, page, pageSize } = options
  const [videos, setVideos] = useState<Video[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [fetchKey, setFetchKey] = useState(0)

  const refetch = useCallback(() => setFetchKey((k) => k + 1), [])

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)

    async function fetchVideos() {
      try {
        let data: { videos: Video[]; total: number }

        if (searchQuery) {
          const params = new URLSearchParams({
            q: searchQuery,
            limit: String(pageSize),
          })
          const res = await fetch(`/api/v1/videos/search?${params}`)
          if (!res.ok) throw new Error(`Search failed: ${res.status}`)
          const json: VideoSearchResponse = await res.json()
          data = { videos: json.videos, total: json.total }
        } else {
          const params = new URLSearchParams({
            limit: String(pageSize),
            offset: String(page * pageSize),
          })
          const res = await fetch(`/api/v1/videos?${params}`)
          if (!res.ok) throw new Error(`Fetch failed: ${res.status}`)
          const json: VideoListResponse = await res.json()
          data = { videos: json.videos, total: json.total }
        }

        if (active) {
          setVideos(sortVideos(data.videos, sortField, sortOrder))
          setTotal(data.total)
          setLoading(false)
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unknown error')
          setLoading(false)
        }
      }
    }

    fetchVideos()

    return () => {
      active = false
    }
  }, [searchQuery, sortField, sortOrder, page, pageSize, fetchKey])

  return { videos, total, loading, error, refetch }
}
