import {
  ChevronRight,
  Download,
  Film,
  MoreHorizontal,
  Pause,
  Play,
  RotateCcw,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
import { cn } from '@/lib/utils'
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

function DeleteDialog({
  cover,
  open,
  onOpenChange,
}: {
  cover: CoverJob
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const remove = useDeleteCover()

  const submit = () => {
    remove.mutate(cover.id, {
      onSuccess: () => {
        toast.success('커버를 삭제했어요.')
        onOpenChange(false)
      },
      onError: (error) => toast.error(error.message),
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>커버 삭제</DialogTitle>
          <DialogDescription>
            '{cover.title}' 커버와 원본 곡, 생성된 오디오가 함께 삭제됩니다. 되돌릴 수
            없어요.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
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
  const [deleteOpen, setDeleteOpen] = useState(false)
  const navigate = useNavigate()

  // 완성된 커버는 행 자체가 스튜디오로 들어가는 입구. 행 안의 인터랙티브
  // 요소(재생·시킹·다운로드·메뉴)에서 시작된 클릭은 내비게이션에서 제외한다.
  const openStudio = (event: React.MouseEvent) => {
    if (!completed) return
    const target = event.target as HTMLElement
    // 드롭다운 메뉴·다이얼로그는 포털로 body에 그려지지만 React 트리를 따라
    // 여기까지 버블된다. DOM상 행 바깥에서 시작된 클릭은 무시한다.
    if (!event.currentTarget.contains(target)) return
    if (target.closest('button, a, canvas')) return
    void navigate(`/covers/${cover.id}/studio`)
  }

  return (
    <li className="flex flex-col">
      <div
        className={cn(
          'group flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-muted/40',
          completed && 'cursor-pointer',
        )}
        onClick={openStudio}
      >
        {completed ? (
          <Button
            size="icon"
            className="size-10 rounded-full"
            onClick={player.toggle}
            aria-label={player.playing ? '일시정지' : '재생'}
          >
            {player.playing ? <Pause className="size-4" /> : <Play className="size-4" />}
          </Button>
        ) : (
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <Play className="size-4" />
          </span>
        )}
        <div className="w-56 min-w-0 shrink">
          {completed ? (
            <Link
              to={`/covers/${cover.id}/studio`}
              className="block truncate text-sm font-semibold hover:text-primary hover:underline"
              title="스튜디오에서 열기"
            >
              {cover.title}
            </Link>
          ) : (
            <p className="truncate text-sm font-semibold">{cover.title}</p>
          )}
          <p className="truncate text-xs text-muted-foreground tabular-nums">
            {voice?.name ?? `보이스 #${cover.voice_id}`} · {formatTranspose(cover.transpose)}
          </p>
        </div>
        <div className="min-w-0 flex-1">
          {inProgress ? (
            <div className="flex items-center gap-3">
              {cover.eta_seconds !== null ? (
                <Progress value={cover.progress * 100} className="flex-1" />
              ) : (
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                  <div className="progress-indeterminate h-full w-1/3 rounded-full bg-primary/70" />
                </div>
              )}
              <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                {coverStatusMeta(cover.status).label}
                {cover.eta_seconds !== null &&
                  ` · 약 ${formatDuration(cover.eta_seconds)} 남음`}
              </span>
            </div>
          ) : cover.status === 'failed' ? (
            <div className="flex items-center gap-2.5">
              <StatusBadge meta={coverStatusMeta(cover.status)} />
              <p className="truncate text-xs text-status-failed">
                {cover.error ?? '생성에 실패했어요.'}
              </p>
            </div>
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
        {completed && (
          <>
            <Button variant="ghost" size="icon" asChild aria-label="다운로드">
              <a href={coverAudioUrl(cover.id, cover.finished_at)} download>
                <Download className="size-4" />
              </a>
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="더 보기">
                  <MoreHorizontal className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onSelect={() => void navigate(`/covers/${cover.id}/video`)}
                >
                  <Film /> 영상 만들기
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => setRemixOpen((open) => !open)}>
                  <SlidersHorizontal /> 보컬 볼륨 조정
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onSelect={() => setDeleteOpen(true)}>
                  <Trash2 /> 삭제
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            <ChevronRight
              className="size-4 shrink-0 text-muted-foreground/40 transition-colors group-hover:text-muted-foreground"
              aria-hidden
            />
          </>
        )}
        {cover.status === 'failed' && (
          <>
            <RetryButton coverId={cover.id} />
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setDeleteOpen(true)}
              aria-label="커버 삭제"
            >
              <Trash2 className="size-4 text-muted-foreground" />
            </Button>
          </>
        )}
      </div>
      {completed && remixOpen && <RemixControl cover={cover} />}
      <DeleteDialog cover={cover} open={deleteOpen} onOpenChange={setDeleteOpen} />
    </li>
  )
}
