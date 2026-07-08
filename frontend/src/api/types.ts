export type VoiceStatus = 'draft' | 'training' | 'ready' | 'failed'

export type TrainingStatus = 'pending' | 'running' | 'completed' | 'failed'

export type CoverStatus =
  | 'pending'
  | 'separating'
  | 'converting'
  | 'mixing'
  | 'completed'
  | 'failed'

export interface Voice {
  id: number
  name: string
  description: string
  status: VoiceStatus
  created_at: string
}

export interface DatasetFile {
  id: number
  original_name: string
  size_bytes: number
  created_at: string
}

export interface VoiceDetail extends Voice {
  dataset_files: DatasetFile[]
}

export interface TrainingJob {
  id: number
  voice_id: number
  status: TrainingStatus
  epochs: number
  progress: number
  eta_seconds: number | null
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface CoverJob {
  id: number
  voice_id: number
  title: string
  transpose: number
  status: CoverStatus
  progress: number
  eta_seconds: number | null
  error: string | null
  created_at: string
  finished_at: string | null
}
