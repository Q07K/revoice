import { apiUrl, deleteRequest, getJson, postForm, postJson, requestJson } from '@/api/client'
import type { CoverJob } from '@/api/types'

export interface CoverCreateInput {
  voiceId: number
  transpose: number
  vocalGain: number
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
  form.append('vocal_gain', String(input.vocalGain))
  form.append('song', input.song)
  return postForm<CoverJob>('/covers', form)
}

export function retryCover(coverId: number): Promise<CoverJob> {
  return requestJson<CoverJob>(`/covers/${coverId}/retry`, { method: 'POST' })
}

export function deleteCover(coverId: number): Promise<void> {
  return deleteRequest(`/covers/${coverId}`)
}

export function remixCover(coverId: number, vocalGain: number): Promise<CoverJob> {
  return postJson<CoverJob>(`/covers/${coverId}/remix`, { vocal_gain: vocalGain })
}

export interface CoverWaveform {
  peaks: number[]
}

export function fetchCoverWaveform(coverId: number): Promise<CoverWaveform> {
  return getJson<CoverWaveform>(`/covers/${coverId}/waveform`)
}

export function coverAudioUrl(coverId: number, version?: string | null): string {
  // version(재믹싱 시 갱신되는 finished_at)을 붙여 브라우저가 이전 오디오를
  // 캐시하지 않도록 한다 — 재믹싱 후 같은 URL이면 옛 파일이 재생된다.
  const suffix = version ? `?v=${encodeURIComponent(version)}` : ''
  return apiUrl(`/covers/${coverId}/audio${suffix}`)
}
