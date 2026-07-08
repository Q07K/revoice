import { Mic } from 'lucide-react'
import { Link } from 'react-router-dom'

import type { Voice } from '@/api/types'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { StatusBadge, voiceStatusMeta } from '@/components/shared/StatusBadge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { CreateVoiceDialog } from '@/features/voices/CreateVoiceDialog'
import { useVoices } from '@/features/voices/queries'
import { formatDate } from '@/lib/format'

function VoiceCard({ voice }: { voice: Voice }) {
  return (
    <Link to={`/voices/${voice.id}`} className="group">
      <Card className="h-full transition-shadow group-hover:shadow-md">
        <CardContent className="flex h-full flex-col gap-2">
          <div className="flex items-start justify-between gap-2">
            <p className="font-semibold">{voice.name}</p>
            <StatusBadge meta={voiceStatusMeta(voice.status)} />
          </div>
          <p className="line-clamp-2 min-h-10 text-sm text-muted-foreground">
            {voice.description.length > 0 ? voice.description : '설명 없음'}
          </p>
          <p className="mt-auto text-xs text-muted-foreground">
            {formatDate(voice.created_at)} 생성
          </p>
        </CardContent>
      </Card>
    </Link>
  )
}

export function VoicesPage() {
  const voices = useVoices()

  return (
    <>
      <PageHeader
        title="보이스 모델"
        description="목소리를 학습시켜 커버에 사용할 보이스 모델을 관리합니다."
        action={<CreateVoiceDialog />}
      />
      {voices.isPending ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((key) => (
            <Skeleton key={key} className="h-36 rounded-2xl" />
          ))}
        </div>
      ) : voices.data === undefined || voices.data.length === 0 ? (
        <EmptyState
          icon={Mic}
          title="아직 보이스 모델이 없어요"
          description="첫 보이스를 만들고 깨끗한 음성 데이터를 올려 학습을 시작해보세요."
          action={<CreateVoiceDialog />}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {voices.data.map((voice) => (
            <VoiceCard key={voice.id} voice={voice} />
          ))}
        </div>
      )}
    </>
  )
}
