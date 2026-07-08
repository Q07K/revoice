import { deleteRequest, getJson, postForm, postJson } from '@/api/client'
import type { DatasetFile, Voice, VoiceDetail } from '@/api/types'

export interface VoiceCreateInput {
  name: string
  description: string
}

export function fetchVoices(): Promise<Voice[]> {
  return getJson<Voice[]>('/voices')
}

export function fetchVoice(voiceId: number): Promise<VoiceDetail> {
  return getJson<VoiceDetail>(`/voices/${voiceId}`)
}

export function createVoice(input: VoiceCreateInput): Promise<Voice> {
  return postJson<Voice>('/voices', input)
}

export function deleteVoice(voiceId: number): Promise<void> {
  return deleteRequest(`/voices/${voiceId}`)
}

export function uploadDatasetFiles(voiceId: number, files: File[]): Promise<DatasetFile[]> {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  return postForm<DatasetFile[]>(`/voices/${voiceId}/dataset`, form)
}
