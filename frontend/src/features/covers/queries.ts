import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createCover, fetchCoverWaveform, fetchCovers, retryCover } from '@/api/covers'
import type { CoverCreateInput } from '@/api/covers'
import type { CoverJob } from '@/api/types'

export const coverKeys = {
  all: ['covers'] as const,
}

const POLL_INTERVAL_MS = 1500

const ACTIVE_STATUSES = new Set<CoverJob['status']>([
  'pending',
  'separating',
  'converting',
  'mixing',
])

export function isCoverInProgress(cover: CoverJob): boolean {
  return ACTIVE_STATUSES.has(cover.status)
}

export function useCovers() {
  return useQuery({
    queryKey: coverKeys.all,
    queryFn: () => fetchCovers(),
    refetchInterval: (query) =>
      query.state.data?.some(isCoverInProgress) ? POLL_INTERVAL_MS : false,
  })
}

export function useCreateCover() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: CoverCreateInput) => createCover(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: coverKeys.all }),
  })
}

export function useCoverWaveform(coverId: number, enabled: boolean) {
  return useQuery({
    queryKey: [...coverKeys.all, coverId, 'waveform'],
    queryFn: () => fetchCoverWaveform(coverId),
    enabled,
    staleTime: Infinity,
  })
}

export function useRetryCover() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (coverId: number) => retryCover(coverId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: coverKeys.all }),
  })
}
