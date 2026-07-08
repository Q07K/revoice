import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { fetchTrainings, startTraining } from '@/api/trainings'
import type { TrainingCreateInput } from '@/api/trainings'
import type { TrainingJob, VoiceDetail } from '@/api/types'
import { createVoice, deleteVoice, fetchVoice, fetchVoices, uploadDatasetFiles } from '@/api/voices'
import type { VoiceCreateInput } from '@/api/voices'

export const voiceKeys = {
  all: ['voices'] as const,
  detail: (voiceId: number) => ['voices', voiceId] as const,
  trainings: (voiceId: number) => ['trainings', voiceId] as const,
}

const POLL_INTERVAL_MS = 1500

export function useVoices() {
  return useQuery({ queryKey: voiceKeys.all, queryFn: fetchVoices })
}

export function useVoice(voiceId: number) {
  return useQuery({
    queryKey: voiceKeys.detail(voiceId),
    queryFn: () => fetchVoice(voiceId),
    refetchInterval: (query) =>
      query.state.data?.status === 'training' ? POLL_INTERVAL_MS : false,
  })
}

function hasActiveTraining(jobs: TrainingJob[] | undefined): boolean {
  return jobs?.some((job) => job.status === 'pending' || job.status === 'running') ?? false
}

export function useVoiceTrainings(voiceId: number) {
  return useQuery({
    queryKey: voiceKeys.trainings(voiceId),
    queryFn: () => fetchTrainings(voiceId),
    refetchInterval: (query) =>
      hasActiveTraining(query.state.data) ? POLL_INTERVAL_MS : false,
  })
}

export function useCreateVoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: VoiceCreateInput) => createVoice(input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: voiceKeys.all }),
  })
}

export function useDeleteVoice() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (voiceId: number) => deleteVoice(voiceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: voiceKeys.all }),
  })
}

export function useUploadDataset(voiceId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (files: File[]) => uploadDatasetFiles(voiceId, files),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: voiceKeys.detail(voiceId) }),
  })
}

export function useStartTraining(voiceId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: TrainingCreateInput) => startTraining(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: voiceKeys.trainings(voiceId) })
      void queryClient.invalidateQueries({ queryKey: voiceKeys.detail(voiceId) })
      void queryClient.invalidateQueries({ queryKey: voiceKeys.all })
    },
  })
}

export function datasetTotalBytes(voice: VoiceDetail): number {
  return voice.dataset_files.reduce((total, file) => total + file.size_bytes, 0)
}
