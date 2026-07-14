import { apiUrl, deleteRequest, getJson, postForm } from '@/api/client'
import type { SeparationJob } from '@/api/types'

export function fetchSeparations(): Promise<SeparationJob[]> {
  return getJson<SeparationJob[]>('/separations')
}

export function createSeparation(song: File): Promise<SeparationJob> {
  const form = new FormData()
  form.append('song', song)
  return postForm<SeparationJob>('/separations', form)
}

export function deleteSeparation(jobId: number): Promise<void> {
  return deleteRequest(`/separations/${jobId}`)
}

export type SeparationStem = 'vocals' | 'instrumental' | 'dry_vocals'

export function separationStemUrl(
  jobId: number,
  stem: SeparationStem,
  version?: string | null,
): string {
  const suffix = version ? `&v=${encodeURIComponent(version)}` : ''
  return apiUrl(`/separations/${jobId}/audio?stem=${stem}${suffix}`)
}
