import { Ban, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import type { TrainingJob, VoiceDetail } from '@/api/types'
import { StatusBadge, trainingStatusMeta } from '@/components/shared/StatusBadge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import {
  useCancelTraining,
  useStartTraining,
  useVoiceTrainings,
} from '@/features/voices/queries'
import { formatDuration } from '@/lib/format'

const DEFAULT_EPOCHS = 100
const MAX_EPOCHS = 500

interface LatestJobProps {
  job: TrainingJob
  onCancel: () => void
  canceling: boolean
}

function LatestJob({ job, onCancel, canceling }: LatestJobProps) {
  const active = job.status === 'running' || job.status === 'pending'
  return (
    <div className="flex flex-col gap-2 rounded-xl bg-muted/60 p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">최근 학습 · {job.epochs} epochs</span>
        <div className="flex items-center gap-2">
          <StatusBadge meta={trainingStatusMeta(job.status)} />
          {active && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 px-2 text-xs text-status-failed hover:text-status-failed"
              onClick={onCancel}
              disabled={canceling}
            >
              <Ban className="size-3.5" />
              {canceling ? '중단 중…' : '중단'}
            </Button>
          )}
        </div>
      </div>
      {active && (
        <>
          <Progress value={job.progress * 100} />
          <div className="flex items-center justify-between text-xs text-muted-foreground tabular-nums">
            <span>{Math.round(job.progress * 100)}%</span>
            <span>
              {job.eta_seconds !== null
                ? `약 ${formatDuration(job.eta_seconds)} 남음`
                : '남은 시간 계산 중…'}
            </span>
          </div>
        </>
      )}
      {job.status === 'failed' && job.error !== null && (
        <p className="text-sm text-status-failed">{job.error}</p>
      )}
    </div>
  )
}

export function TrainingCard({ voice }: { voice: VoiceDetail }) {
  const [epochs, setEpochs] = useState(DEFAULT_EPOCHS)
  const trainings = useVoiceTrainings(voice.id)
  const startTraining = useStartTraining(voice.id)
  const cancelTraining = useCancelTraining(voice.id)

  const latestJob = trainings.data?.[0]
  const isTraining = voice.status === 'training'
  const hasDataset = voice.dataset_files.length > 0

  const handleCancel = () => {
    if (latestJob === undefined) return
    cancelTraining.mutate(latestJob.id, {
      onSuccess: () => toast.success('학습 중단을 요청했어요. 곧 정리됩니다.'),
      onError: (error) => toast.error(error.message),
    })
  }

  const submit = () => {
    startTraining.mutate(
      { voice_id: voice.id, epochs },
      {
        onSuccess: () => toast.success('학습을 시작했어요. 진행률이 여기에 표시됩니다.'),
        onError: (error) => toast.error(error.message),
      },
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>학습</CardTitle>
        <CardDescription>
          데이터셋으로 RVC v2 보이스 모델을 학습합니다. RVC v2는 과적합이 빨라요 —
          권장 50~200, 데이터가 많을수록 낮게 잡는 게 좋습니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {latestJob !== undefined && (
          <LatestJob
            job={latestJob}
            onCancel={handleCancel}
            canceling={cancelTraining.isPending}
          />
        )}
        {voice.status === 'ready' && (
          <p className="text-sm text-status-ready">
            학습이 끝났어요.{' '}
            <Link to="/covers/new" className="font-semibold underline underline-offset-2">
              이 보이스로 커버 만들러 가기 →
            </Link>
          </p>
        )}
        <div className="flex items-end gap-3">
          <div className="flex flex-col gap-2">
            <Label htmlFor="epochs">Epochs</Label>
            <Input
              id="epochs"
              type="number"
              min={1}
              max={MAX_EPOCHS}
              value={epochs}
              onChange={(event) => setEpochs(Number(event.target.value))}
              className="w-28"
              disabled={isTraining}
            />
          </div>
          <Button
            onClick={submit}
            disabled={!hasDataset || isTraining || startTraining.isPending}
          >
            <Sparkles className="size-4" />
            {isTraining ? '학습 중…' : voice.status === 'ready' ? '다시 학습' : '학습 시작'}
          </Button>
        </div>
        {!hasDataset && (
          <p className="text-xs text-muted-foreground">
            학습을 시작하려면 먼저 데이터셋 오디오를 올려주세요.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
