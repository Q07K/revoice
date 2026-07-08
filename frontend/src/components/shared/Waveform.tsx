import { useEffect, useRef } from 'react'

import { cn } from '@/lib/utils'

interface WaveformProps {
  /** 실제 오디오에서 추출한 정규화(0~1) 피크 값들. */
  peaks: number[]
  /** 재생 위치 (0~1). 지난 구간은 진하게, 남은 구간은 흐리게 그린다. */
  progress: number
  /** 클릭한 위치(0~1)로 시킹. 지정하면 커서/키보드 조작이 활성화된다. */
  onSeek?: (fraction: number) => void
  className?: string
}

const BAR_WIDTH = 2
const BAR_GAP = 2
const MIN_BAR_HEIGHT = 2

function draw(canvas: HTMLCanvasElement, peaks: number[], progress: number): void {
  const context = canvas.getContext('2d')
  if (context === null) return

  const ratio = window.devicePixelRatio || 1
  const width = canvas.clientWidth
  const height = canvas.clientHeight
  if (width === 0 || height === 0 || peaks.length === 0) return

  canvas.width = width * ratio
  canvas.height = height * ratio
  context.scale(ratio, ratio)
  context.clearRect(0, 0, width, height)

  const color = getComputedStyle(canvas).color
  const barCount = Math.floor(width / (BAR_WIDTH + BAR_GAP))
  context.fillStyle = color

  for (let i = 0; i < barCount; i += 1) {
    const peakIndex = Math.floor((i / barCount) * peaks.length)
    const peak = peaks[peakIndex] ?? 0
    const barHeight = Math.max(MIN_BAR_HEIGHT, peak * height)
    const played = progress > 0 && i / barCount <= progress
    context.globalAlpha = played ? 0.95 : 0.35
    context.fillRect(i * (BAR_WIDTH + BAR_GAP), (height - barHeight) / 2, BAR_WIDTH, barHeight)
  }
}

export function Waveform({ peaks, progress, onSeek, className }: WaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (canvas === null) return

    draw(canvas, peaks, progress)
    const observer = new ResizeObserver(() => draw(canvas, peaks, progress))
    observer.observe(canvas)
    return () => observer.disconnect()
  }, [peaks, progress])

  const handleClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (onSeek === undefined) return
    const bounds = event.currentTarget.getBoundingClientRect()
    if (bounds.width > 0) {
      onSeek((event.clientX - bounds.left) / bounds.width)
    }
  }

  return (
    <canvas
      ref={canvasRef}
      onClick={handleClick}
      className={cn(
        'h-7 w-full text-primary',
        onSeek !== undefined && 'cursor-pointer',
        className,
      )}
      role={onSeek !== undefined ? 'slider' : undefined}
      aria-label={onSeek !== undefined ? '재생 위치' : undefined}
      aria-valuemin={onSeek !== undefined ? 0 : undefined}
      aria-valuemax={onSeek !== undefined ? 100 : undefined}
      aria-valuenow={onSeek !== undefined ? Math.round(progress * 100) : undefined}
    />
  )
}
