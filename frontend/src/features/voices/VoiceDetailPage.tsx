import { ChevronLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { StatusBadge, voiceStatusMeta } from '@/components/shared/StatusBadge'
import { Skeleton } from '@/components/ui/skeleton'
import { DatasetCard } from '@/features/voices/DatasetCard'
import { DeleteVoiceDialog } from '@/features/voices/DeleteVoiceDialog'
import { TrainingCard } from '@/features/voices/TrainingCard'
import { useVoice } from '@/features/voices/queries'

export function VoiceDetailPage() {
  const params = useParams<{ voiceId: string }>()
  const voiceId = Number(params.voiceId)
  const voice = useVoice(voiceId)

  if (voice.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-64 rounded-xl" />
        <Skeleton className="h-52 rounded-2xl" />
        <Skeleton className="h-52 rounded-2xl" />
      </div>
    )
  }

  if (voice.data === undefined) {
    return (
      <p className="text-sm text-muted-foreground">
        보이스를 찾을 수 없어요.{' '}
        <Link to="/voices" className="underline underline-offset-2">
          목록으로 돌아가기
        </Link>
      </p>
    )
  }

  return (
    <>
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            to="/voices"
            className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="size-4" /> 보이스 모델
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{voice.data.name}</h1>
            <StatusBadge meta={voiceStatusMeta(voice.data.status)} />
          </div>
          {voice.data.description.length > 0 && (
            <p className="mt-1 text-sm text-muted-foreground">{voice.data.description}</p>
          )}
        </div>
        <DeleteVoiceDialog voice={voice.data} />
      </div>
      <DatasetCard voice={voice.data} />
      <TrainingCard voice={voice.data} />
    </>
  )
}
