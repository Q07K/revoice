import { LibraryBig, Mic, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import type { CoverJob, Voice } from '@/api/types'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { StatusBadge, voiceStatusMeta } from '@/components/shared/StatusBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { CoverListItem } from '@/features/covers/CoverListItem'
import { useCovers } from '@/features/covers/queries'
import { CreateVoiceDialog } from '@/features/voices/CreateVoiceDialog'
import { useVoices } from '@/features/voices/queries'

const RECENT_COVER_COUNT = 5

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-1">
        <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {label}
        </span>
        <span className="text-3xl font-bold tabular-nums">{value}</span>
      </CardContent>
    </Card>
  )
}

function StatRow({ voices, covers }: { voices: Voice[]; covers: CoverJob[] }) {
  const trainingCount = voices.filter((voice) => voice.status === 'training').length
  const completedCovers = covers.filter((cover) => cover.status === 'completed').length
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StatTile label="보이스 모델" value={voices.length} />
      <StatTile label="학습 중" value={trainingCount} />
      <StatTile label="완성된 커버" value={completedCovers} />
    </div>
  )
}

function VoiceSection({ voices }: { voices: Voice[] }) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
          보이스 모델
        </h2>
        <Link
          to="/voices"
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          전체 보기 →
        </Link>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {voices.slice(0, 3).map((voice) => (
          <Link key={voice.id} to={`/voices/${voice.id}`}>
            <Card className="h-full transition-shadow hover:shadow-md">
              <CardContent className="flex flex-col gap-2">
                <p className="truncate font-semibold">{voice.name}</p>
                <StatusBadge meta={voiceStatusMeta(voice.status)} />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  )
}

function RecentCoversSection({ covers, voices }: { covers: CoverJob[]; voices: Voice[] }) {
  const voiceById = new Map(voices.map((voice) => [voice.id, voice]))
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">
          최근 커버
        </h2>
        <Link to="/library" className="text-sm text-muted-foreground hover:text-foreground">
          라이브러리 →
        </Link>
      </div>
      {covers.length === 0 ? (
        <EmptyState
          icon={LibraryBig}
          title="아직 만든 커버가 없어요"
          description="학습이 끝난 보이스로 첫 커버를 만들어보세요."
          action={
            <Button asChild>
              <Link to="/covers/new">
                <Sparkles className="size-4" /> 커버 만들기
              </Link>
            </Button>
          }
        />
      ) : (
        <Card className="py-0">
          <ul className="divide-y">
            {covers.slice(0, RECENT_COVER_COUNT).map((cover) => (
              <CoverListItem
                key={cover.id}
                cover={cover}
                voice={voiceById.get(cover.voice_id)}
              />
            ))}
          </ul>
        </Card>
      )}
    </section>
  )
}

export function DashboardPage() {
  const voices = useVoices()
  const covers = useCovers()

  if (voices.isPending || covers.isPending) {
    return (
      <>
        <PageHeader title="대시보드" description="보이스와 커버 작업을 한눈에 봅니다." />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((key) => (
            <Skeleton key={key} className="h-24 rounded-2xl" />
          ))}
        </div>
        <Skeleton className="h-40 rounded-2xl" />
      </>
    )
  }

  const voiceList = voices.data ?? []
  const coverList = covers.data ?? []

  return (
    <>
      <PageHeader
        title="대시보드"
        description="보이스와 커버 작업을 한눈에 봅니다."
        action={
          <div className="flex gap-2">
            <CreateVoiceDialog />
            <Button variant="secondary" asChild>
              <Link to="/covers/new">
                <Sparkles className="size-4" /> 커버 만들기
              </Link>
            </Button>
          </div>
        }
      />
      {voiceList.length === 0 ? (
        <EmptyState
          icon={Mic}
          title="Revoice에 오신 걸 환영해요"
          description="먼저 보이스 모델을 만들고, 깨끗한 음성 데이터로 학습을 시작해보세요."
          action={<CreateVoiceDialog />}
        />
      ) : (
        <>
          <StatRow voices={voiceList} covers={coverList} />
          <VoiceSection voices={voiceList} />
          <RecentCoversSection covers={coverList} voices={voiceList} />
        </>
      )}
    </>
  )
}
