import { Download, Pause, Play, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'

import { coverAudioUrl } from '@/api/covers'
import type { CoverJob, Voice } from '@/api/types'
import { StatusBadge, coverStatusMeta } from '@/components/shared/StatusBadge'
import { Waveform } from '@/components/shared/Waveform'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { isCoverInProgress, useCoverWaveform, useRetryCover } from '@/features/covers/queries'
import { useAudioPlayer } from '@/features/covers/useAudioPlayer'
import { formatDuration, formatTranspose } from '@/lib/format'

function RetryButton({ coverId }: { coverId: number }) {
  const retry = useRetryCover()
  const submit = () => {
    retry.mutate(coverId, {
      onSuccess: () => toast.success('커버 생성을 다시 시작했어요.'),
      onError: (error) => toast.error(error.message),
    })
  }
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={submit}
      disabled={retry.isPending}
      aria-label="다시 시도"
    >
      <RotateCcw className="size-4" />
    </Button>
  )
}

interface CoverListItemProps {
  cover: CoverJob
  voice: Voice | undefined
}

export function CoverListItem({ cover, voice }: CoverListItemProps) {
  const inProgress = isCoverInProgress(cover)
  const completed = cover.status === 'completed'
  const player = useAudioPlayer(coverAudioUrl(cover.id))
  const waveform = useCoverWaveform(cover.id, completed)

  return (
    <li className="flex items-center gap-4 px-5 py-4">
      {completed ? (
        <Button
          size="icon"
          className="rounded-full"
          onClick={player.toggle}
          aria-label={player.playing ? '일시정지' : '재생'}
        >
          {player.playing ? <Pause className="size-4" /> : <Play className="size-4" />}
        </Button>
      ) : (
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <Play className="size-4" />
        </span>
      )}
      <div className="w-44 shrink-0">
        <p className="truncate text-sm font-semibold">{cover.title}</p>
        <p className="truncate text-xs text-muted-foreground">
          {voice?.name ?? `보이스 #${cover.voice_id}`} · {formatTranspose(cover.transpose)}
        </p>
      </div>
      <div className="min-w-0 flex-1">
        {inProgress ? (
          cover.eta_seconds !== null ? (
            <div className="flex items-center gap-3">
              <Progress value={cover.progress * 100} className="flex-1" />
              <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                약 {formatDuration(cover.eta_seconds)} 남음
              </span>
            </div>
          ) : (
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div className="progress-indeterminate h-full w-1/3 rounded-full bg-primary/70" />
            </div>
          )
        ) : cover.status === 'failed' ? (
          <p className="truncate text-xs text-status-failed">
            {cover.error ?? '생성에 실패했어요.'}
          </p>
        ) : waveform.data === undefined ? (
          <Skeleton className="h-7 w-full rounded-md" />
        ) : (
          <Waveform
            peaks={waveform.data.peaks}
            progress={player.progress}
            onSeek={player.seek}
          />
        )}
      </div>
      <StatusBadge meta={coverStatusMeta(cover.status)} />
      {completed && (
        <Button variant="ghost" size="icon" asChild aria-label="다운로드">
          <a href={coverAudioUrl(cover.id)} download>
            <Download className="size-4" />
          </a>
        </Button>
      )}
      {cover.status === 'failed' && <RetryButton coverId={cover.id} />}
    </li>
  )
}
