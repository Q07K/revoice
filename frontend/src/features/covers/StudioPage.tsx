import {
  ArrowLeft,
  Download,
  Film,
  Mic,
  Pause,
  Play,
  SkipBack,
} from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { coverExportMp3Url } from '@/api/covers'
import type { CoverJob } from '@/api/types'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Slider } from '@/components/ui/slider'
import { useCovers, useRemixCover } from '@/features/covers/queries'
import { useMultitrack } from '@/features/covers/useMultitrack'
import type { StemKind } from '@/features/covers/useMultitrack'
import { useVoices } from '@/features/voices/queries'
import { cn } from '@/lib/utils'
import { formatTranspose } from '@/lib/format'

const HEAD_W = 176
const LANES: { key: StemKind; label: string; sub: string; waveClass: string }[] = [
  { key: 'vocal', label: '변환 보컬', sub: 'AI 보이스', waveClass: 'text-primary' },
  { key: 'instrumental', label: '반주 (MR)', sub: '분리됨', waveClass: 'text-muted-foreground' },
]

function fmt(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

function drawWave(canvas: HTMLCanvasElement, buffer: AudioBuffer) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  if (w === 0 || h === 0) return
  canvas.width = w * dpr
  canvas.height = h * dpr
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  // 캔버스는 CSS 변수를 못 읽으므로 엘리먼트의 계산된 color를 파형 색으로 쓴다.
  const color = getComputedStyle(canvas).color
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, w, h)
  const data = buffer.getChannelData(0)
  const bars = Math.max(1, Math.floor(w / 3))
  const step = Math.max(1, Math.floor(data.length / bars))
  const mid = h / 2
  ctx.fillStyle = color
  for (let i = 0; i < bars; i++) {
    let peak = 0
    for (let j = 0; j < step; j += 64) {
      const v = Math.abs(data[i * step + j] || 0)
      if (v > peak) peak = v
    }
    const amp = Math.max(1, peak * h * 0.46)
    ctx.globalAlpha = 0.4 + 0.55 * peak
    ctx.fillRect(i * 3, mid - amp, 2, amp * 2)
  }
  ctx.globalAlpha = 1
}

function TrackWave({ buffer, waveClass }: { buffer: AudioBuffer | null; waveClass: string }) {
  const ref = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = ref.current
    if (!canvas || !buffer) return
    const render = () => drawWave(canvas, buffer)
    render()
    const ro = new ResizeObserver(render)
    ro.observe(canvas)
    // 테마(라이트/다크) 전환 시 계산된 color가 바뀌므로 다시 그린다.
    const mo = new MutationObserver(render)
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => {
      ro.disconnect()
      mo.disconnect()
    }
  }, [buffer])
  return <canvas ref={ref} className={cn('absolute inset-0 size-full', waveClass)} />
}

function ChannelToggle({
  on,
  label,
  ariaLabel,
  activeClass,
  onClick,
}: {
  on: boolean
  label: string
  ariaLabel: string
  activeClass: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      aria-pressed={on}
      className={cn(
        'grid size-6 shrink-0 place-items-center rounded-md text-[10px] font-bold transition-colors',
        on ? activeClass : 'bg-muted text-muted-foreground hover:text-foreground',
      )}
    >
      {label}
    </button>
  )
}

export function StudioPage() {
  const { coverId: param } = useParams()
  const coverId = Number(param)
  const navigate = useNavigate()

  const covers = useCovers()
  const voices = useVoices()
  const cover: CoverJob | undefined = covers.data?.find((c) => c.id === coverId)
  const voiceName = voices.data?.find((v) => v.id === cover?.voice_id)?.name

  const mt = useMultitrack(coverId)
  const remix = useRemixCover()

  const lanesRef = useRef<HTMLDivElement>(null)
  const playheadRef = useRef<HTMLDivElement>(null)
  const timeRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (mt.status !== 'ready') return
    let raf = 0
    const tick = () => {
      const pos = mt.getPosition()
      const container = lanesRef.current
      if (container && playheadRef.current && mt.duration > 0) {
        const usable = container.clientWidth - HEAD_W
        playheadRef.current.style.left = `${HEAD_W + (pos / mt.duration) * usable}px`
      }
      if (timeRef.current) timeRef.current.textContent = fmt(pos)
      raf = requestAnimationFrame(tick)
    }
    tick()
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mt.status, mt.isPlaying, mt.duration, mt.getPosition])

  const seekFromClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    mt.seek(((e.clientX - rect.left) / rect.width) * mt.duration)
  }

  // applyMix가 저장하는 값과 같은 공식: 트랙 볼륨 비율을 0.5~2.5로 클램프한 보컬 게인
  const ratio = mt.tracks.vocal.volume / Math.max(mt.tracks.instrumental.volume, 0.01)
  const mixedGain = Math.min(2.5, Math.max(0.5, Number(ratio.toFixed(1))))

  const applyMix = () => {
    remix.mutate(
      { coverId, vocalGain: mixedGain },
      {
        onSuccess: () => toast.success(`이 믹스로 저장했어요 (보컬 ${mixedGain}×).`),
        onError: (error) => toast.error(error.message),
      },
    )
  }

  const notReady = !covers.isLoading && (!cover || cover.status !== 'completed')
  const mixDirty = cover !== undefined && mixedGain !== cover.vocal_gain

  return (
    <div className="fixed inset-0 flex flex-col bg-background text-sm text-foreground">
      {/* 상단 바: 돌아가기 · 곡 정보 · 내보내기 */}
      <header className="flex items-center gap-3 border-b bg-card px-4 py-3">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/library">
            <ArrowLeft className="size-4" /> 라이브러리
          </Link>
        </Button>
        <div className="h-5 w-px bg-border" aria-hidden />
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="truncate font-semibold">
            {cover ? cover.title.replace(/\.[^.]+$/, '') : '스튜디오'}
          </span>
          {cover && (
            <>
              <span className="flex shrink-0 items-center gap-1 rounded-full bg-accent px-2.5 py-0.5 text-xs font-semibold text-accent-foreground">
                <Mic className="size-3" />
                {voiceName ?? `보이스 #${cover.voice_id}`}
              </span>
              <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                {formatTranspose(cover.transpose)}
              </span>
            </>
          )}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link to={`/covers/${coverId}/video`}>
              <Film className="size-4" /> 영상 만들기
            </Link>
          </Button>
          {cover?.status === 'completed' && (
            <Button size="sm" asChild>
              <a href={coverExportMp3Url(coverId, cover.finished_at)} download>
                <Download className="size-4" /> MP3 내보내기
              </a>
            </Button>
          )}
        </div>
      </header>

      {notReady ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
          완성된 커버만 스튜디오에서 열 수 있어요.
          <Button variant="secondary" asChild>
            <Link to="/library">라이브러리로 돌아가기</Link>
          </Button>
        </div>
      ) : mt.status === 'error' ? (
        <div className="flex flex-1 items-center justify-center px-6 text-center text-status-failed">
          {mt.error} — 예전에 만든 커버라면 새로 만들어야 트랙이 생겨요.
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          {/* 재생 컨트롤 */}
          <div className="flex items-center justify-center gap-3 border-b bg-card/50 px-4 py-3">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => mt.seek(0)}
              aria-label="처음으로"
            >
              <SkipBack className="size-4" />
            </Button>
            <Button
              size="icon"
              className="size-11 rounded-full"
              onClick={mt.toggle}
              disabled={mt.status !== 'ready'}
              aria-label={mt.isPlaying ? '일시정지' : '재생'}
            >
              {mt.isPlaying ? <Pause className="size-5" /> : <Play className="size-5" />}
            </Button>
            <span className="w-24 text-sm text-muted-foreground tabular-nums">
              <span ref={timeRef} className="font-semibold text-foreground">
                0:00
              </span>{' '}
              / {fmt(mt.duration)}
            </span>
          </div>

          {/* 타임 눈금 */}
          <div
            className="flex h-6 border-b bg-muted/40 text-[10px] text-muted-foreground"
            style={{ paddingLeft: HEAD_W }}
          >
            {[0, 0.2, 0.4, 0.6, 0.8].map((f) => (
              <span key={f} className="flex-1 border-l pl-1.5 pt-1 tabular-nums">
                {fmt(mt.duration * f)}
              </span>
            ))}
          </div>

          {/* 트랙 레인 */}
          <div ref={lanesRef} className="relative flex flex-1 flex-col">
            {LANES.map(({ key, label, sub, waveClass }) => {
              const t = mt.tracks[key]
              return (
                <div key={key} className="flex min-h-28 flex-1 border-b">
                  <div
                    className="flex flex-col justify-between border-r bg-card p-3"
                    style={{ width: HEAD_W }}
                  >
                    <div>
                      <p className="text-[13px] font-semibold">{label}</p>
                      <p className="text-[11px] text-muted-foreground">{sub}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <ChannelToggle
                        on={t.muted}
                        label="M"
                        ariaLabel={`${label} 음소거`}
                        activeClass="bg-destructive text-destructive-foreground"
                        onClick={() => mt.toggleMute(key)}
                      />
                      <ChannelToggle
                        on={t.solo}
                        label="S"
                        ariaLabel={`${label} 솔로`}
                        activeClass="bg-primary text-primary-foreground"
                        onClick={() => mt.toggleSolo(key)}
                      />
                      <Slider
                        min={0}
                        max={2.5}
                        step={0.1}
                        value={[t.volume]}
                        onValueChange={(values) => mt.setVolume(key, values[0] ?? t.volume)}
                        className="flex-1"
                        aria-label={`${label} 볼륨`}
                      />
                      <span className="w-8 shrink-0 text-right text-[11px] font-semibold text-primary tabular-nums">
                        {t.volume.toFixed(1)}×
                      </span>
                    </div>
                  </div>
                  <div
                    className={cn(
                      'relative min-w-0 flex-1 cursor-pointer bg-muted/20 transition-opacity',
                      t.muted && 'opacity-35',
                    )}
                    onClick={seekFromClick}
                  >
                    {mt.status === 'ready' ? (
                      <TrackWave buffer={mt.bufferOf(key)} waveClass={waveClass} />
                    ) : (
                      <Skeleton className="absolute inset-2 rounded-lg" />
                    )}
                  </div>
                </div>
              )
            })}
            <div
              ref={playheadRef}
              className="pointer-events-none absolute inset-y-0 w-0.5 bg-chart-3 shadow-[0_0_8px_var(--chart-3)]"
              style={{ left: HEAD_W }}
            />
          </div>

          {/* 믹스 저장 */}
          <div className="flex flex-wrap items-center gap-3 px-5 py-4">
            <p className="text-xs text-muted-foreground">
              트랙 볼륨은 재생하며 실시간으로 들려요. 저장하면 최종본(MP3·영상)에 반영됩니다.
            </p>
            <Button
              size="sm"
              className="ml-auto"
              onClick={applyMix}
              disabled={remix.isPending || mt.status !== 'ready' || !mixDirty}
            >
              {remix.isPending ? '저장 중…' : '이 믹스로 저장'}
            </Button>
          </div>

          {/* 변환 설정 정보 */}
          {cover && (
            <div className="mt-auto flex flex-wrap items-center gap-x-5 gap-y-1 border-t bg-card/50 px-5 py-3 text-xs text-muted-foreground">
              <span className="font-medium text-foreground/70">변환 설정</span>
              <span className="tabular-nums">키 {formatTranspose(cover.transpose)}</span>
              <span className="tabular-nums">음색 반영 {cover.index_rate.toFixed(2)}</span>
              <span className="tabular-nums">자음·숨소리 보호 {cover.protect.toFixed(2)}</span>
              <span className="tabular-nums">볼륨 곡선 {cover.volume_envelope.toFixed(2)}</span>
              <button
                type="button"
                onClick={() => void navigate('/covers/new')}
                className="ml-auto font-medium text-primary underline-offset-2 hover:underline"
              >
                설정 바꿔 새로 만들기
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
