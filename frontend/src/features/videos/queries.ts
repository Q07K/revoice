import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createVideo, deleteVideo, fetchVideos } from '@/api/videos'
import type { VideoCreateInput } from '@/api/videos'
import type { VideoJob } from '@/api/types'

export const videoKeys = {
  all: ['videos'] as const,
  forCover: (coverId: number) => ['videos', 'cover', coverId] as const,
}

const POLL_INTERVAL_MS = 1500

const ACTIVE_STATUSES = new Set<VideoJob['status']>(['pending', 'rendering'])

export function isVideoInProgress(job: VideoJob): boolean {
  return ACTIVE_STATUSES.has(job.status)
}

export function useCoverVideos(coverId: number) {
  return useQuery({
    queryKey: videoKeys.forCover(coverId),
    queryFn: () => fetchVideos(coverId),
    refetchInterval: (query) =>
      query.state.data?.some(isVideoInProgress) ? POLL_INTERVAL_MS : false,
  })
}

export function useCreateVideo(coverId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: VideoCreateInput) => createVideo(input),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: videoKeys.forCover(coverId) }),
  })
}

export function useDeleteVideo(coverId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (jobId: number) => deleteVideo(jobId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: videoKeys.forCover(coverId) }),
  })
}
