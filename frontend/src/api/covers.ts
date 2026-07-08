import { apiUrl, getJson, postForm, requestJson } from '@/api/client'
import type { CoverJob } from '@/api/types'

export interface CoverCreateInput {
  voiceId: number
  transpose: number
  song: File
}

export function fetchCovers(voiceId?: number): Promise<CoverJob[]> {
  const query = voiceId === undefined ? '' : `?voice_id=${voiceId}`
  return getJson<CoverJob[]>(`/covers${query}`)
}

export function fetchCover(coverId: number): Promise<CoverJob> {
  return getJson<CoverJob>(`/covers/${coverId}`)
}

export function createCover(input: CoverCreateInput): Promise<CoverJob> {
  const form = new FormData()
  form.append('voice_id', String(input.voiceId))
  form.append('transpose', String(input.transpose))
  form.append('song', input.song)
  return postForm<CoverJob>('/covers', form)
}

export function retryCover(coverId: number): Promise<CoverJob> {
  return requestJson<CoverJob>(`/covers/${coverId}/retry`, { method: 'POST' })
}

export interface CoverWaveform {
  peaks: number[]
}

export function fetchCoverWaveform(coverId: number): Promise<CoverWaveform> {
  return getJson<CoverWaveform>(`/covers/${coverId}/waveform`)
}

export function coverAudioUrl(coverId: number): string {
  return apiUrl(`/covers/${coverId}/audio`)
}
