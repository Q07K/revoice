import { Download, Music2, Scissors, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { separationStemUrl } from '@/api/separations'
import type { SeparationStem } from '@/api/separations'
import type { SeparationJob } from '@/api/types'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { SongDropzone } from '@/components/shared/SongDropzone'
import { StatusBadge, separationStatusMeta } from '@/components/shared/StatusBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  isSeparationInProgress,
  useCreateSeparation,
  useDeleteSeparation,
  useSeparations,
} from '@/features/separations/queries'
import { formatDuration } from '@/lib/format'

const STEM_LABELS: Record<SeparationStem, string> = {
  vocals: '보컬',
  instrumental: '반주',
  dry_vocals: '보컬 · 리버브 제거',
}

function StemRow({ job, stem }: { job: SeparationJob; stem: SeparationStem }) {
  const label = STEM_LABELS[stem]
  const url = separationStemUrl(job.id, stem, job.finished_at)
  return (
    <div className="flex flex-col gap-2 rounded-lg bg-muted/50 p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">{label}</span>
        <a href={url} download>
          <Button variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-xs">
            <Download className="size-3.5" />
            내려받기
          </Button>
        </a>
      </div>
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <audio controls preload="none" src={url} className="w-full" />
    </div>
  )
}

function SeparationCard({ job }: { job: SeparationJob }) {
  const deleteSeparation = useDeleteSeparation()
  const inProgress = isSeparationInProgress(job)

  const remove = () => {
    deleteSeparation.mutate(job.id, {
      onError: (error) => toast.error(error.message),
    })
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2">
          <Music2 className="size-4 shrink-0 text-muted-foreground" />
          <span className="truncate text-sm font-medium">{job.title}</span>
        </span>
        <div className="flex items-center gap-2">
          <StatusBadge meta={separationStatusMeta(job.status)} />
          {!inProgress && (
            <Button
              variant="ghost"
              size="icon"
              className="size-7 text-muted-foreground hover:text-status-failed"
              onClick={remove}
              disabled={deleteSeparation.isPending}
              aria-label="삭제"
            >
              <Trash2 className="size-4" />
            </Button>
          )}
        </div>
      </div>

      {inProgress && (
        <div className="flex flex-col gap-1.5">
          <Progress value={job.progress * 100} />
          <div className="flex justify-between text-xs text-muted-foreground tabular-nums">
            <span>보컬 분리 중…</span>
            <span>
              {job.eta_seconds !== null
                ? `약 ${formatDuration(job.eta_seconds)} 남음`
                : '남은 시간 계산 중…'}
            </span>
          </div>
        </div>
      )}

      {job.status === 'completed' && (
        <div className={`grid gap-3 sm:grid-cols-2 ${job.has_dry_vocals ? 'lg:grid-cols-3' : ''}`}>
          <StemRow job={job} stem="vocals" />
          <StemRow job={job} stem="instrumental" />
          {job.has_dry_vocals && <StemRow job={job} stem="dry_vocals" />}
        </div>
      )}

      {job.status === 'failed' && (
        <p className="text-sm text-status-failed">{job.error ?? '분리에 실패했어요.'}</p>
      )}
    </div>
  )
}

export function SeparationPage() {
  const [song, setSong] = useState<File | null>(null)
  const separations = useSeparations()
  const createSeparation = useCreateSeparation()

  const submit = () => {
    if (song === null) return
    createSeparation.mutate(song, {
      onSuccess: () => {
        toast.success('보컬 분리를 시작했어요. 아래에서 진행 상황을 볼 수 있어요.')
        setSong(null)
      },
      onError: (error) => toast.error(error.message),
    })
  }

  const jobs = separations.data ?? []

  return (
    <>
      <PageHeader
        title="반주 제거"
        description="곡을 올리면 보컬 · 반주(MR) · 리버브까지 지운 보컬, 세 가지로 분리해요. 리버브 제거 보컬은 깨끗한 학습 데이터로 쓰기 좋아요."
      />
      <div className="flex flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle>곡 올리기</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <SongDropzone file={song} onChange={setSong} />
            <Button
              onClick={submit}
              disabled={song === null || createSeparation.isPending}
              className="w-fit"
            >
              <Scissors className="size-4" />
              {createSeparation.isPending ? '시작하는 중…' : '보컬·반주 분리'}
            </Button>
          </CardContent>
        </Card>

        {jobs.length === 0 ? (
          <EmptyState
            icon={Scissors}
            title="아직 분리한 곡이 없어요"
            description="곡을 올리면 보컬과 반주로 나눠 드려요."
          />
        ) : (
          <div className="flex flex-col gap-3">
            {jobs.map((job) => (
              <SeparationCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>
    </>
  )
}
