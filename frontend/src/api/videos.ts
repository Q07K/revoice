import { apiUrl, deleteRequest, getJson, postForm } from '@/api/client'
import type { VideoAspect, VideoJob, VideoVisual } from '@/api/types'

export interface VideoCreateInput {
  coverId: number
  title: string
  subtitle: string
  visual: VideoVisual
  aspect: VideoAspect
  image: File | null
}

export function fetchVideos(coverId?: number): Promise<VideoJob[]> {
  const query = coverId === undefined ? '' : `?cover_id=${coverId}`
  return getJson<VideoJob[]>(`/videos${query}`)
}

export function createVideo(input: VideoCreateInput): Promise<VideoJob> {
  const form = new FormData()
  form.append('cover_id', String(input.coverId))
  form.append('title', input.title)
  form.append('subtitle', input.subtitle)
  form.append('visual', input.visual)
  form.append('aspect', input.aspect)
  if (input.image) form.append('image', input.image)
  return postForm<VideoJob>('/videos', form)
}

export function deleteVideo(jobId: number): Promise<void> {
  return deleteRequest(`/videos/${jobId}`)
}

export function videoDownloadUrl(jobId: number, version?: string | null): string {
  const suffix = version ? `?v=${encodeURIComponent(version)}` : ''
  return apiUrl(`/videos/${jobId}/download${suffix}`)
}
