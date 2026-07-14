import { LayoutList, LibraryBig, Rows3, Search, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import type { CoverJob } from '@/api/types'
import { EmptyState } from '@/components/shared/EmptyState'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { CoverCompactItem } from '@/features/covers/CoverCompactItem'
import { CoverListItem } from '@/features/covers/CoverListItem'
import { useBatchDeleteCovers, useCovers } from '@/features/covers/queries'
import { useVoices } from '@/features/voices/queries'
import { cn } from '@/lib/utils'

type SortKey = 'latest' | 'oldest' | 'title'
type ViewMode = 'list' | 'compact'

const VIEW_STORAGE_KEY = 'revoice-library-view'

function loadViewMode(): ViewMode {
  // 훑어보기가 기본 과제라 컴팩트가 기본값; 리스트(파형) 보기는 선택.
  return localStorage.getItem(VIEW_STORAGE_KEY) === 'list' ? 'list' : 'compact'
}

function sortCovers(covers: CoverJob[], sort: SortKey): CoverJob[] {
  const sorted = [...covers]
  if (sort === 'title') sorted.sort((a, b) => a.title.localeCompare(b.title, 'ko'))
  else if (sort === 'oldest') sorted.sort((a, b) => a.id - b.id)
  else sorted.sort((a, b) => b.id - a.id)
  return sorted
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? 'border-primary bg-accent font-semibold text-accent-foreground'
          : 'bg-card text-foreground hover:border-primary/40',
      )}
    >
      {children}
    </button>
  )
}

export function LibraryPage() {
  const covers = useCovers()
  const voices = useVoices()
  const batchDelete = useBatchDeleteCovers()

  const [query, setQuery] = useState('')
  const [voiceFilter, setVoiceFilter] = useState<number | null>(null)
  const [onlyCompleted, setOnlyCompleted] = useState(false)
  const [sort, setSort] = useState<SortKey>('latest')
  const [view, setViewState] = useState<ViewMode>(loadViewMode)
  const [selection, setSelection] = useState<ReadonlySet<number>>(new Set())
  const [confirmDelete, setConfirmDelete] = useState<number[] | null>(null)

  const setView = (mode: ViewMode) => {
    setViewState(mode)
    setSelection(new Set())
    localStorage.setItem(VIEW_STORAGE_KEY, mode)
  }

  const voiceById = new Map((voices.data ?? []).map((voice) => [voice.id, voice]))

  // 보이스 칩: 커버가 있는 보이스만, 커버 수 내림차순.
  const voiceCounts = useMemo(() => {
    const counts = new Map<number, number>()
    for (const cover of covers.data ?? []) {
      counts.set(cover.voice_id, (counts.get(cover.voice_id) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [covers.data])

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const matched = (covers.data ?? []).filter((cover) => {
      if (voiceFilter !== null && cover.voice_id !== voiceFilter) return false
      if (onlyCompleted && cover.status !== 'completed') return false
      if (needle && !cover.title.toLowerCase().includes(needle)) return false
      return true
    })
    return sortCovers(matched, sort)
  }, [covers.data, query, voiceFilter, onlyCompleted, sort])

  const hasFilter = query.trim() !== '' || voiceFilter !== null || onlyCompleted
  const total = covers.data?.length ?? 0

  const toggleSelect = (coverId: number) => {
    setSelection((previous) => {
      const next = new Set(previous)
      if (next.has(coverId)) next.delete(coverId)
      else next.add(coverId)
      return next
    })
  }

  const runDelete = (ids: number[]) => {
    batchDelete.mutate(ids, {
      onSuccess: (result) => {
        toast.success(
          result.skipped > 0
            ? `${result.deleted}개를 삭제했어요. 진행 중인 ${result.skipped}개는 건너뛰었어요.`
            : `${result.deleted}개를 삭제했어요.`,
        )
        setSelection(new Set())
        setConfirmDelete(null)
      },
      onError: (error) => toast.error(error.message),
    })
  }

  return (
    <>
      <PageHeader
        title="라이브러리"
        description="만든 커버를 듣고 내려받을 수 있어요. 진행 중인 작업도 여기에 표시됩니다."
        action={
          <div className="flex items-center gap-2">
            <div className="flex rounded-lg border p-0.5" role="radiogroup" aria-label="보기 방식">
              <Button
                variant={view === 'list' ? 'secondary' : 'ghost'}
                size="icon"
                className="size-8"
                role="radio"
                aria-checked={view === 'list'}
                aria-label="리스트 보기"
                onClick={() => setView('list')}
              >
                <LayoutList className="size-4" />
              </Button>
              <Button
                variant={view === 'compact' ? 'secondary' : 'ghost'}
                size="icon"
                className="size-8"
                role="radio"
                aria-checked={view === 'compact'}
                aria-label="컴팩트 보기"
                onClick={() => setView('compact')}
              >
                <Rows3 className="size-4" />
              </Button>
            </div>
            <Button asChild>
              <Link to="/covers/new">
                <Sparkles className="size-4" /> 새 커버
              </Link>
            </Button>
          </div>
        }
      />

      {/* 검색·필터 툴바 */}
      {total > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <div className="relative min-w-44 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="곡 제목 검색"
              className="h-9 pl-9"
              aria-label="곡 제목 검색"
            />
          </div>
          <Select
            value={voiceFilter === null ? 'all' : String(voiceFilter)}
            onValueChange={(value) => setVoiceFilter(value === 'all' ? null : Number(value))}
          >
            <SelectTrigger
              className={cn('h-9 w-44', voiceFilter !== null && 'border-primary text-accent-foreground')}
              aria-label="보이스 필터"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">모든 보이스 · {total}</SelectItem>
              {voiceCounts.map(([id, count]) => (
                <SelectItem key={id} value={String(id)}>
                  {voiceById.get(id)?.name ?? `보이스 #${id}`} · {count}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FilterChip
            active={onlyCompleted}
            onClick={() => setOnlyCompleted((previous) => !previous)}
          >
            완료만
          </FilterChip>
          <Select value={sort} onValueChange={(value) => setSort(value as SortKey)}>
            <SelectTrigger className="h-9 w-28" aria-label="정렬">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="latest">최신순</SelectItem>
              <SelectItem value="oldest">오래된순</SelectItem>
              <SelectItem value="title">제목순</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* 컴팩트 모드 선택 액션 바 */}
      {view === 'compact' && selection.size > 0 && (
        <div className="mb-3 flex items-center gap-3 rounded-xl border border-primary/40 bg-accent/50 px-4 py-2">
          <span className="text-sm font-semibold tabular-nums">{selection.size}개 선택됨</span>
          <Button
            variant="destructive"
            size="sm"
            className="h-7"
            onClick={() => setConfirmDelete([...selection])}
            disabled={batchDelete.isPending}
          >
            선택 삭제
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7"
            onClick={() => setSelection(new Set())}
          >
            선택 해제
          </Button>
        </div>
      )}

      {covers.isPending ? (
        <div className="flex flex-col gap-3">
          {[0, 1, 2].map((key) => (
            <Skeleton key={key} className="h-16 rounded-lg" />
          ))}
        </div>
      ) : total === 0 ? (
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
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed px-6 py-12 text-center">
          <p className="text-sm text-muted-foreground">조건에 맞는 커버가 없어요.</p>
          {hasFilter && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setQuery('')
                setVoiceFilter(null)
                setOnlyCompleted(false)
              }}
            >
              필터 초기화
            </Button>
          )}
        </div>
      ) : (
        <Card className="py-0">
          <ul className={cn('divide-y', view === 'compact' && 'py-1')}>
            {filtered.map((cover) =>
              view === 'compact' ? (
                <CoverCompactItem
                  key={cover.id}
                  cover={cover}
                  voice={voiceById.get(cover.voice_id)}
                  selected={selection.has(cover.id)}
                  onToggleSelect={toggleSelect}
                  onDelete={(target) => setConfirmDelete([target.id])}
                />
              ) : (
                <CoverListItem
                  key={cover.id}
                  cover={cover}
                  voice={voiceById.get(cover.voice_id)}
                />
              ),
            )}
          </ul>
        </Card>
      )}

      <Dialog
        open={confirmDelete !== null}
        onOpenChange={(open) => !open && setConfirmDelete(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>커버 삭제</DialogTitle>
            <DialogDescription>
              선택한 {confirmDelete?.length ?? 0}개 커버와 원본 곡, 생성된 오디오가 함께
              삭제됩니다. 되돌릴 수 없어요.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setConfirmDelete(null)}>
              취소
            </Button>
            <Button
              variant="destructive"
              onClick={() => confirmDelete && runDelete(confirmDelete)}
              disabled={batchDelete.isPending}
            >
              {batchDelete.isPending ? '삭제 중…' : '삭제'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
