import type { TrainingStatus } from '@/api/types'
import { cn } from '@/lib/utils'
import { formatDuration } from '@/lib/format'

// Stage boundaries mirror the backend progress budget: dataset cleanup 0–8%
// (trainings/service.py), then the trainer's own budget (app/engines/applio.py)
// rescaled into the remaining 8–100% — preprocess ~8–13% · extract ~13–17% ·
// train ~17–96% · finalize ~96–100%. The bar streams smoothly inside each
// slice, and each segment is sized by its share of wall-clock time.
const STAGES = [
  { key: 'cleanup', label: '데이터 정제', short: '정제', start: 0, end: 8 },
  { key: 'preprocess', label: '전처리', short: '전처리', start: 8, end: 13 },
  { key: 'extract', label: '특징 추출', short: '추출', start: 13, end: 17 },
  { key: 'train', label: '학습', short: '학습', start: 17, end: 96 },
  { key: 'finalize', label: '마무리', short: '마무리', start: 96, end: 100 },
] as const

// bar segments and their labels share this weight so labels sit under segments
const weight = (stage: (typeof STAGES)[number]) => Math.max(stage.end - stage.start, 5)

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

function activeStage(percent: number) {
  const index = STAGES.findIndex((stage) => percent < stage.end)
  return index === -1 ? STAGES.length - 1 : index
}

interface TrainingProgressProps {
  progress: number
  etaSeconds: number | null
  status: TrainingStatus
}

export function TrainingProgress({ progress, etaSeconds, status }: TrainingProgressProps) {
  const done = status === 'completed'
  const percent = done ? 100 : clamp(progress * 100, 0, 100)
  const activeIndex = done ? STAGES.length : activeStage(percent)

  return (
    <div className="flex flex-col gap-2.5">
      {/* weighted segment bar with the overall % inside it. Two stacked labels
          (muted over the track, light over the fill) are clipped at the fill
          edge, so the digits stay put — no reflow — while the colour flips as
          the fill sweeps past. */}
      <div className="relative flex h-5 gap-[3px]">
        {STAGES.map((stage, index) => {
          const isDone = done || index < activeIndex
          const isActive = !done && index === activeIndex
          const fillWidth = isDone
            ? 100
            : isActive
              ? Math.round(clamp((percent - stage.start) / (stage.end - stage.start), 0, 1) * 100)
              : 0
          return (
            <div
              key={stage.key}
              className="relative overflow-hidden rounded-md bg-muted"
              style={{ flexGrow: weight(stage), flexBasis: 0 }}
            >
              <span
                className={cn(
                  'absolute inset-y-0 left-0 rounded-md transition-[width] duration-300 ease-linear',
                  isDone ? 'bg-status-ready' : 'bg-primary',
                )}
                style={{ width: `${fillWidth}%` }}
              />
            </div>
          )
        })}
        <span className="pointer-events-none absolute inset-0 grid place-items-center text-[11px] font-semibold tabular-nums text-foreground">
          {Math.round(percent)}%
        </span>
        <span
          className="pointer-events-none absolute inset-0 grid place-items-center text-[11px] font-semibold tabular-nums text-primary-foreground"
          style={{ clipPath: `inset(0 ${100 - percent}% 0 0)` }}
        >
          {Math.round(percent)}%
        </span>
      </div>

      {/* stage names — current bold, done green. no per-step % here (that jitters) */}
      <div className="flex flex-wrap items-center gap-x-1 gap-y-0.5 text-[11px] leading-tight">
        {STAGES.map((stage, index) => {
          const isDone = done || index < activeIndex
          const isActive = !done && index === activeIndex
          return (
            <span key={stage.key} className="flex items-center gap-1">
              {index > 0 && <span className="text-muted-foreground/50">›</span>}
              <span
                className={cn(
                  isActive
                    ? 'font-semibold text-primary'
                    : isDone
                      ? 'text-status-ready'
                      : 'text-muted-foreground',
                )}
              >
                {stage.label}
              </span>
            </span>
          )
        })}
        {!done && etaSeconds !== null && (
          <span className="ml-auto text-muted-foreground tabular-nums">
            약 {formatDuration(etaSeconds)} 남음
          </span>
        )}
      </div>
    </div>
  )
}
