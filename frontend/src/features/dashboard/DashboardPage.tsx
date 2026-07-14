import { ArrowRight, LibraryBig, Mic, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import type { CoverJob, Voice } from '@/api/types'
import { EmptyState } from '@/components/shared/EmptyState'
import { StatusBadge, voiceStatusMeta } from '@/components/shared/StatusBadge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { CoverListItem } from '@/features/covers/CoverListItem'
import { useCovers } from '@/features/covers/queries'
import { CreateVoiceDialog } from '@/features/voices/CreateVoiceDialog'
import { useVoices } from '@/features/voices/queries'

const RECENT_COVER_COUNT = 5

function Hero({ hasReadyVoice }: { hasReadyVoice: boolean }) {
  return (
    <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary to-primary/75 px-8 py-10 text-primary-foreground">
      <div className="relative z-10 flex flex-col items-start gap-5">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tight text-balance">
            내 목소리로 다시 부르는 노래
          </h1>
          <p className="max-w-md text-sm text-primary-foreground/85">
            좋아하는 곡을 올리면 학습한 보이스가 대신 불러드려요. 분리부터 믹싱까지
            전부 자동이에요.
          </p>
        </div>
        {hasReadyVoice ? (
          <Button
            size="lg"
            asChild
            className="bg-primary-foreground text-primary hover:bg-primary-foreground/90"
          >
            <Link to="/covers/new">
              <Sparkles className="size-4" /> 커버 만들기
            </Link>
          </Button>
        ) : (
          <p className="rounded-xl bg-primary-foreground/15 px-4 py-2.5 text-sm">
            먼저 보이스 모델을 학습시키면 커버를 만들 수 있어요.
          </p>
        )}
      </div>
      <SoundBars />
    </section>
  )
}

/* 히어로 우측의 장식용 이퀄라이저 바 */
function SoundBars() {
  const heights = [34, 58, 42, 72, 50, 88, 62, 44, 70, 36]
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-y-0 right-8 hidden items-center gap-2 opacity-25 md:flex"
    >
      {heights.map((height, index) => (
        <span
          key={index}
          className="w-2.5 rounded-full bg-primary-foreground"
          style={{ height: `${height}%` }}
        />
      ))}
    </div>
  )
}

function SectionHeader({ title, to, cta }: { title: string; to: string; cta: string }) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <Link
        to={to}
        className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        {cta} <ArrowRight className="size-3.5" />
      </Link>
    </div>
  )
}

function VoiceSection({ voices }: { voices: Voice[] }) {
  return (
    <section className="flex flex-col gap-3">
      <SectionHeader title="내 보이스" to="/voices" cta="전체 보기" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {voices.slice(0, 3).map((voice) => (
          <Link key={voice.id} to={`/voices/${voice.id}`}>
            <Card className="h-full py-4 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md">
              <div className="flex items-center gap-3 px-4">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent text-base font-bold text-accent-foreground">
                  {voice.name.slice(0, 1)}
                </span>
                <p className="min-w-0 flex-1 truncate font-semibold">{voice.name}</p>
                <StatusBadge meta={voiceStatusMeta(voice.status)} />
              </div>
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
      <SectionHeader title="최근 커버" to="/library" cta="라이브러리" />
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
        <Skeleton className="h-52 rounded-3xl" />
        <Skeleton className="h-24 rounded-2xl" />
        <Skeleton className="h-64 rounded-2xl" />
      </>
    )
  }

  const voiceList = voices.data ?? []
  const coverList = covers.data ?? []
  const hasReadyVoice = voiceList.some((voice) => voice.status === 'ready')

  return (
    <>
      <Hero hasReadyVoice={hasReadyVoice} />
      {voiceList.length === 0 ? (
        <EmptyState
          icon={Mic}
          title="첫 보이스 모델을 만들어보세요"
          description="깨끗한 음성 데이터로 목소리를 학습시키면, 그 목소리로 어떤 곡이든 부를 수 있어요."
          action={<CreateVoiceDialog />}
        />
      ) : (
        <>
          <RecentCoversSection covers={coverList} voices={voiceList} />
          <VoiceSection voices={voiceList} />
        </>
      )}
    </>
  )
}
