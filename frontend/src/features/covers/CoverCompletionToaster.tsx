import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import type { CoverStatus } from '@/api/types'
import { useCovers } from '@/features/covers/queries'

/**
 * 커버 폴링 결과를 지켜보다가 '진행 중 → 완성' 전환 순간에 토스트를 띄운다.
 * 어느 페이지에 있든 만들기 → 결과 확인 동선이 끊기지 않도록 레이아웃에 상주한다.
 */
export function CoverCompletionToaster() {
  const covers = useCovers()
  const navigate = useNavigate()
  const prevStatuses = useRef<Map<number, CoverStatus> | null>(null)

  useEffect(() => {
    const data = covers.data
    if (data === undefined) return
    const prev = prevStatuses.current
    prevStatuses.current = new Map(data.map((cover) => [cover.id, cover.status]))
    // 첫 로드에는 이미 완성돼 있던 커버들이므로 알리지 않는다.
    if (prev === null) return

    for (const cover of data) {
      const before = prev.get(cover.id)
      if (before === undefined || before === 'completed' || cover.status !== 'completed') {
        continue
      }
      toast.success(`'${cover.title.replace(/\.[^.]+$/, '')}' 커버가 완성됐어요!`, {
        duration: 8000,
        action: {
          label: '스튜디오에서 열기',
          onClick: () => void navigate(`/covers/${cover.id}/studio`),
        },
      })
    }
  }, [covers.data, navigate])

  return null
}
