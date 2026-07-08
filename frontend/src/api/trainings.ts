import { getJson, postJson } from '@/api/client'
import type { TrainingJob } from '@/api/types'

export interface TrainingCreateInput {
  voice_id: number
  epochs: number
}

export function fetchTrainings(voiceId?: number): Promise<TrainingJob[]> {
  const query = voiceId === undefined ? '' : `?voice_id=${voiceId}`
  return getJson<TrainingJob[]>(`/trainings${query}`)
}

export function startTraining(input: TrainingCreateInput): Promise<TrainingJob> {
  return postJson<TrainingJob>('/trainings', input)
}
