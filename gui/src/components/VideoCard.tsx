import type { Video } from '../hooks/useVideos'

interface VideoCardProps {
  video: Video
}

function formatDuration(video: Video): string {
  if (video.frame_rate_denominator === 0 || video.frame_rate_numerator === 0) {
    return '0:00'
  }
  const fps = video.frame_rate_numerator / video.frame_rate_denominator
  const totalSeconds = Math.floor(video.duration_frames / fps)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
  }
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

export default function VideoCard({ video }: VideoCardProps) {
  return (
    <div
      className="group rounded border border-gray-700 bg-gray-900 overflow-hidden"
      data-testid={`video-card-${video.id}`}
    >
      <div className="relative aspect-video bg-gray-800">
        <img
          src={`/api/v1/videos/${video.id}/thumbnail`}
          alt={video.filename}
          className="h-full w-full object-cover"
          loading="lazy"
          data-testid={`video-thumbnail-${video.id}`}
        />
        <span
          className="absolute bottom-1 right-1 rounded bg-black/80 px-1.5 py-0.5 text-xs text-gray-200"
          data-testid={`video-duration-${video.id}`}
        >
          {formatDuration(video)}
        </span>
      </div>
      <div className="p-2">
        <p
          className="truncate text-sm text-gray-200"
          title={video.filename}
          data-testid={`video-filename-${video.id}`}
        >
          {video.filename}
        </p>
      </div>
    </div>
  )
}
