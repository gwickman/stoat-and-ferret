import type { Video } from '../hooks/useVideos'
import VideoCard from './VideoCard'

interface VideoGridProps {
  videos: Video[]
  loading: boolean
  error: string | null
}

export default function VideoGrid({ videos, loading, error }: VideoGridProps) {
  if (loading) {
    return (
      <div className="py-12 text-center text-gray-400" data-testid="video-grid-loading">
        Loading videos...
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-12 text-center text-red-400" data-testid="video-grid-error">
        {error}
      </div>
    )
  }

  if (videos.length === 0) {
    return (
      <div className="py-12 text-center text-gray-400" data-testid="video-grid-empty">
        No videos found. Scan a directory to add videos.
      </div>
    )
  }

  return (
    <div
      className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
      data-testid="video-grid"
    >
      {videos.map((video) => (
        <VideoCard key={video.id} video={video} />
      ))}
    </div>
  )
}
