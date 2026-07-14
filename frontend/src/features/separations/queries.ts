import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  createSeparation,
  deleteSeparation,
  fetchSeparations,
} from '@/api/separations'
import type { SeparationJob } from '@/api/types'

export const separationKeys = {
  all: ['separations'] as const,
}

const POLL_INTERVAL_MS = 1500

const ACTIVE_STATUSES = new Set<SeparationJob['status']>(['pending', 'separating'])

export function isSeparationInProgress(job: SeparationJob): boolean {
  return ACTIVE_STATUSES.has(job.status)
}

export function useSeparations() {
  return useQuery({
    queryKey: separationKeys.all,
    queryFn: () => fetchSeparations(),
    refetchInterval: (query) =>
      query.state.data?.some(isSeparationInProgress) ? POLL_INTERVAL_MS : false,
  })
}

export function useCreateSeparation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (song: File) => createSeparation(song),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: separationKeys.all }),
  })
}

export function useDeleteSeparation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (jobId: number) => deleteSeparation(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: separationKeys.all }),
  })
}
