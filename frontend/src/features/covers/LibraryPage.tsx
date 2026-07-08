import { LibraryBig, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { CoverListItem } from '@/features/covers/CoverListItem'
import { useCovers } from '@/features/covers/queries'
import { useVoices } from '@/features/voices/queries'

export function LibraryPage() {
  const covers = useCovers()
  const voices = useVoices()

  const voiceById = new Map((voices.data ?? []).map((voice) => [voice.id, voice]))

  return (
    <>
      <PageHeader
        title="라이브러리"
        description="만든 커버를 듣고 내려받을 수 있어요. 진행 중인 작업도 여기에 표시됩니다."
        action={
          <Button asChild>
            <Link to="/covers/new">
              <Sparkles className="size-4" /> 새 커버
            </Link>
          </Button>
        }
      />
      {covers.isPending ? (
        <div className="flex flex-col gap-3">
          {[0, 1, 2].map((key) => (
            <Skeleton key={key} className="h-16 rounded-2xl" />
          ))}
        </div>
      ) : covers.data === undefined || covers.data.length === 0 ? (
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
            {covers.data.map((cover) => (
              <CoverListItem
                key={cover.id}
                cover={cover}
                voice={voiceById.get(cover.voice_id)}
              />
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}
