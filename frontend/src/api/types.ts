export type VoiceStatus = 'draft' | 'training' | 'ready' | 'failed'

export type TrainingStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'

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
  auto_transpose: boolean
  vocal_gain: number
  index_rate: number
  protect: number
  volume_envelope: number
  status: CoverStatus
  progress: number
  eta_seconds: number | null
  error: string | null
  created_at: string
  finished_at: string | null
}

export type VideoStatus = 'pending' | 'rendering' | 'completed' | 'failed'
export type VideoVisual = 'image' | 'wave' | 'spectrum'
export type VideoAspect = '16:9' | '9:16'

export interface VideoJob {
  id: number
  cover_id: number
  title: string
  subtitle: string
  visual: VideoVisual
  aspect: VideoAspect
  status: VideoStatus
  progress: number
  eta_seconds: number | null
  error: string | null
  created_at: string
  finished_at: string | null
}

export type SeparationStatus = 'pending' | 'separating' | 'completed' | 'failed'

export interface SeparationJob {
  id: number
  title: string
  status: SeparationStatus
  progress: number
  eta_seconds: number | null
  has_vocals: boolean
  has_instrumental: boolean
  has_dry_vocals: boolean
  error: string | null
  created_at: string
  finished_at: string | null
}
