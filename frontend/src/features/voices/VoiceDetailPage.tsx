import { ChevronLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { StatusBadge, voiceStatusMeta } from '@/components/shared/StatusBadge'
import { Skeleton } from '@/components/ui/skeleton'
import { DatasetCard } from '@/features/voices/DatasetCard'
import { DeleteVoiceDialog } from '@/features/voices/DeleteVoiceDialog'
import { EditVoiceDialog } from '@/features/voices/EditVoiceDialog'
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
        <Skeleton className="h-52 rounded-lg" />
        <Skeleton className="h-52 rounded-lg" />
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
      <div className="flex items-start justify-between gap-4 border-b border-border/70 pb-5">
        <div className="flex flex-col gap-1.5">
          <Link
            to="/voices"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="size-3.5" /> 보이스 모델
          </Link>
          <div className="flex items-center gap-2.5">
            <span className="h-5 w-1 rounded-full bg-primary" aria-hidden />
            <h1 className="text-[22px] font-bold tracking-tight">{voice.data.name}</h1>
            <StatusBadge meta={voiceStatusMeta(voice.data.status)} />
          </div>
          {voice.data.description.length > 0 && (
            <p className="text-sm text-muted-foreground">{voice.data.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1">
          <EditVoiceDialog voice={voice.data} />
          <DeleteVoiceDialog voice={voice.data} />
        </div>
      </div>
      <DatasetCard voice={voice.data} />
      <TrainingCard voice={voice.data} />
    </>
  )
}
