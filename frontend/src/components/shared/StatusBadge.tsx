import type { CoverStatus, TrainingStatus, VoiceStatus } from '@/api/types'
import { cn } from '@/lib/utils'

export type StatusKind = 'ready' | 'running' | 'draft' | 'failed'

export interface StatusMeta {
  label: string
  kind: StatusKind
}

const KIND_CLASSES: Record<StatusKind, string> = {
  ready: 'bg-status-ready-bg text-status-ready',
  running: 'bg-status-running-bg text-status-running',
  draft: 'bg-status-draft-bg text-status-draft',
  failed: 'bg-status-failed-bg text-status-failed',
}

export function voiceStatusMeta(status: VoiceStatus): StatusMeta {
  const meta: Record<VoiceStatus, StatusMeta> = {
    draft: { label: '초안', kind: 'draft' },
    training: { label: '학습 중', kind: 'running' },
    ready: { label: '사용 가능', kind: 'ready' },
    failed: { label: '학습 실패', kind: 'failed' },
  }
  return meta[status]
}

export function trainingStatusMeta(status: TrainingStatus): StatusMeta {
  const meta: Record<TrainingStatus, StatusMeta> = {
    pending: { label: '대기 중', kind: 'draft' },
    running: { label: '학습 중', kind: 'running' },
    completed: { label: '완료', kind: 'ready' },
    failed: { label: '실패', kind: 'failed' },
  }
  return meta[status]
}

export function coverStatusMeta(status: CoverStatus): StatusMeta {
  const meta: Record<CoverStatus, StatusMeta> = {
    pending: { label: '대기 중', kind: 'draft' },
    separating: { label: '보컬 분리 중', kind: 'running' },
    converting: { label: '목소리 변환 중', kind: 'running' },
    mixing: { label: '믹싱 중', kind: 'running' },
    completed: { label: '완성', kind: 'ready' },
    failed: { label: '실패', kind: 'failed' },
  }
  return meta[status]
}

interface StatusBadgeProps {
  meta: StatusMeta
  className?: string
}

export function StatusBadge({ meta, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex w-fit items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
        KIND_CLASSES[meta.kind],
        className,
      )}
    >
      {meta.label}
    </span>
  )
}
