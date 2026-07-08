import { Download, Pause, Play, RotateCcw, SlidersHorizontal, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { coverAudioUrl } from '@/api/covers'
import type { CoverJob, Voice } from '@/api/types'
import { StatusBadge, coverStatusMeta } from '@/components/shared/StatusBadge'
import { Waveform } from '@/components/shared/Waveform'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Slider } from '@/components/ui/slider'
import {
  isCoverInProgress,
  useCoverWaveform,
  useDeleteCover,
  useRemixCover,
  useRetryCover,
} from '@/features/covers/queries'
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

function RemixControl({ cover }: { cover: CoverJob }) {
  const [vocalGain, setVocalGain] = useState(cover.vocal_gain)
  const remix = useRemixCover()

  const apply = () => {
    remix.mutate(
      { coverId: cover.id, vocalGain },
      {
        onSuccess: () => toast.success('보컬 볼륨을 다시 적용했어요.'),
        onError: (error) => toast.error(error.message),
      },
    )
  }

  return (
    <div className="flex items-center gap-3 border-t bg-muted/30 px-5 py-3">
      <span className="w-20 shrink-0 text-xs font-medium text-muted-foreground">
        보컬 볼륨
      </span>
      <Slider
        min={0.5}
        max={2.5}
        step={0.1}
        value={[vocalGain]}
        onValueChange={(values) => setVocalGain(values[0] ?? cover.vocal_gain)}
        className="flex-1"
        disabled={remix.isPending}
      />
      <span className="w-10 shrink-0 text-right text-xs font-semibold text-primary tabular-nums">
        {vocalGain.toFixed(1)}×
      </span>
      <Button
        size="sm"
        className="h-7"
        onClick={apply}
        disabled={remix.isPending || vocalGain === cover.vocal_gain}
      >
        {remix.isPending ? '적용 중…' : '적용'}
      </Button>
    </div>
  )
}

function DeleteButton({ cover }: { cover: CoverJob }) {
  const [open, setOpen] = useState(false)
  const remove = useDeleteCover()

  const submit = () => {
    remove.mutate(cover.id, {
      onSuccess: () => {
        toast.success('커버를 삭제했어요.')
        setOpen(false)
      },
      onError: (error) => toast.error(error.message),
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="커버 삭제">
          <Trash2 className="size-4 text-muted-foreground" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>커버 삭제</DialogTitle>
          <DialogDescription>
            '{cover.title}' 커버와 원본 곡, 생성된 오디오가 함께 삭제됩니다. 되돌릴 수
            없어요.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="secondary" onClick={() => setOpen(false)}>
            취소
          </Button>
          <Button variant="destructive" onClick={submit} disabled={remove.isPending}>
            {remove.isPending ? '삭제 중…' : '삭제'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

interface CoverListItemProps {
  cover: CoverJob
  voice: Voice | undefined
}

export function CoverListItem({ cover, voice }: CoverListItemProps) {
  const inProgress = isCoverInProgress(cover)
  const completed = cover.status === 'completed'
  const player = useAudioPlayer(coverAudioUrl(cover.id, cover.finished_at))
  const waveform = useCoverWaveform(cover.id, completed)
  const [remixOpen, setRemixOpen] = useState(false)

  return (
    <li className="flex flex-col">
      <div className="flex items-center gap-4 px-5 py-4">
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
          <>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setRemixOpen((open) => !open)}
              aria-label="보컬 볼륨 조정"
              aria-pressed={remixOpen}
            >
              <SlidersHorizontal className="size-4" />
            </Button>
            <Button variant="ghost" size="icon" asChild aria-label="다운로드">
              <a href={coverAudioUrl(cover.id, cover.finished_at)} download>
                <Download className="size-4" />
              </a>
            </Button>
          </>
        )}
        {cover.status === 'failed' && <RetryButton coverId={cover.id} />}
        {!inProgress && <DeleteButton cover={cover} />}
      </div>
      {completed && remixOpen && <RemixControl cover={cover} />}
    </li>
  )
}
