import { Film, Pause, Play, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { coverAudioUrl } from '@/api/covers'
import type { CoverJob, Voice } from '@/api/types'
import { StatusBadge, coverStatusMeta } from '@/components/shared/StatusBadge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Progress } from '@/components/ui/progress'
import { isCoverInProgress } from '@/features/covers/queries'
import { useAudioPlayer } from '@/features/covers/useAudioPlayer'
import { cn } from '@/lib/utils'
import { formatDuration, formatRelativeDate, formatTranspose } from '@/lib/format'

interface CoverCompactItemProps {
  cover: CoverJob
  voice: Voice | undefined
  selected: boolean
  onToggleSelect: (coverId: number) => void
  onDelete: (cover: CoverJob) => void
}

/** 컴팩트 보기: 파형 없이 절반 높이 행 + 다중 선택. 훑어보기·정리 전용이라
 * 볼륨 재조정 같은 세부 조작은 리스트 보기/스튜디오에 남긴다. */
export function CoverCompactItem({
  cover,
  voice,
  selected,
  onToggleSelect,
  onDelete,
}: CoverCompactItemProps) {
  const completed = cover.status === 'completed'
  const inProgress = isCoverInProgress(cover)
  const player = useAudioPlayer(coverAudioUrl(cover.id, cover.finished_at))
  const navigate = useNavigate()

  const openStudio = (event: React.MouseEvent) => {
    if (!completed) return
    const target = event.target as HTMLElement
    if (!event.currentTarget.contains(target)) return
    if (target.closest('button, a, input')) return
    void navigate(`/covers/${cover.id}/studio`)
  }

  return (
    <li
      className={cn(
        'flex items-center gap-3 px-4 py-1.5 transition-colors',
        completed && 'cursor-pointer hover:bg-muted/40',
        selected && 'bg-accent/60',
      )}
      onClick={openStudio}
    >
      <input
        type="checkbox"
        className="size-3.5 shrink-0 accent-primary"
        checked={selected}
        disabled={inProgress}
        onChange={() => onToggleSelect(cover.id)}
        aria-label={`${cover.title} 선택`}
      />
      {completed ? (
        <Button
          size="icon"
          variant={player.playing ? 'default' : 'secondary'}
          className="size-6 shrink-0 rounded-full"
          onClick={player.toggle}
          aria-label={player.playing ? '일시정지' : '재생'}
        >
          {player.playing ? <Pause className="size-3" /> : <Play className="size-3" />}
        </Button>
      ) : (
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <Play className="size-3" />
        </span>
      )}
      <span className="w-64 min-w-0 shrink truncate text-[13px] font-medium">
        {cover.title}
      </span>
      <span className="w-24 shrink-0 truncate text-xs text-muted-foreground">
        {voice?.name ?? `보이스 #${cover.voice_id}`}
      </span>
      <span className="w-14 shrink-0 text-xs text-muted-foreground tabular-nums">
        {formatTranspose(cover.transpose)}
      </span>
      <span className="flex min-w-0 flex-1 items-center gap-2">
        {!completed && <StatusBadge meta={coverStatusMeta(cover.status)} />}
        {inProgress && (
          <>
            <Progress value={cover.progress * 100} className="h-1.5 max-w-44 flex-1" />
            <span className="text-[11px] font-semibold text-status-running tabular-nums">
              {Math.round(cover.progress * 100)}%
            </span>
            {cover.eta_seconds !== null && (
              <span className="whitespace-nowrap text-[11px] text-muted-foreground">
                약 {formatDuration(cover.eta_seconds)}
              </span>
            )}
          </>
        )}
      </span>
      <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
        {formatRelativeDate(cover.created_at)}
      </span>
      {completed ? (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="size-6 text-muted-foreground"
              aria-label="더 보기"
            >
              ⋯
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => void navigate(`/covers/${cover.id}/video`)}>
              <Film /> 영상 만들기
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onSelect={() => onDelete(cover)}>
              <Trash2 /> 삭제
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ) : (
        <span className="size-6 shrink-0" aria-hidden />
      )}
    </li>
  )
}
