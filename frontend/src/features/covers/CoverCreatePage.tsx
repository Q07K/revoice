import { ChevronDown, Info, Sparkles } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import type { Voice } from '@/api/types'
import { PageHeader } from '@/components/shared/PageHeader'
import { SongDropzone } from '@/components/shared/SongDropzone'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useCreateCover } from '@/features/covers/queries'
import { useVoices } from '@/features/voices/queries'
import { cn } from '@/lib/utils'
import { formatTranspose } from '@/lib/format'

const DEFAULT_VOCAL_GAIN = 1.5
const DEFAULT_INDEX_RATE = 0.5
const DEFAULT_PROTECT = 0.33
const DEFAULT_VOLUME_ENVELOPE = 1.0

interface OptionSliderProps {
  label: string
  tip: string
  value: number
  display: string
  min: number
  max: number
  step: number
  onChange: (value: number) => void
}

function OptionSlider({ label, tip, value, display, min, max, step, onChange }: OptionSliderProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Label>{label}</Label>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label={`${label} 설명`}
                className="text-muted-foreground transition-colors hover:text-foreground focus-visible:text-foreground focus-visible:outline-none"
              >
                <Info className="size-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent>{tip}</TooltipContent>
          </Tooltip>
        </div>
        <span className="text-sm font-semibold text-primary tabular-nums">{display}</span>
      </div>
      <Slider
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={(values) => onChange(values[0] ?? value)}
      />
    </div>
  )
}

function StepCard({
  step,
  title,
  children,
}: {
  step: number
  title: string
  children: ReactNode
}) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-4">
        <div className="flex items-center gap-2.5">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
            {step}
          </span>
          <h2 className="font-semibold">{title}</h2>
        </div>
        {children}
      </CardContent>
    </Card>
  )
}

function VoicePicker({
  voices,
  selectedId,
  onSelect,
}: {
  voices: Voice[]
  selectedId: number | null
  onSelect: (id: number) => void
}) {
  return (
    <div className="grid grid-cols-2 gap-2.5 lg:grid-cols-3" role="radiogroup" aria-label="보이스 선택">
      {voices.map((voice) => {
        const selected = voice.id === selectedId
        return (
          <button
            key={voice.id}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onSelect(voice.id)}
            className={cn(
              'flex items-center gap-2.5 rounded-xl border-2 px-3.5 py-3 text-left transition-all',
              selected
                ? 'border-primary bg-accent'
                : 'border-border bg-card hover:border-primary/40 hover:bg-muted/40',
            )}
          >
            <span
              className={cn(
                'flex size-9 shrink-0 items-center justify-center rounded-full text-sm font-bold',
                selected
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-accent text-accent-foreground',
              )}
            >
              {voice.name.slice(0, 1)}
            </span>
            <span className="min-w-0 truncate text-sm font-semibold">{voice.name}</span>
          </button>
        )
      })}
    </div>
  )
}

export function CoverCreatePage() {
  const [voiceId, setVoiceId] = useState<number | null>(null)
  const [autoTranspose, setAutoTranspose] = useState(true)
  const [transpose, setTranspose] = useState(0)
  const [vocalGain, setVocalGain] = useState(DEFAULT_VOCAL_GAIN)
  const [indexRate, setIndexRate] = useState(DEFAULT_INDEX_RATE)
  const [protect, setProtect] = useState(DEFAULT_PROTECT)
  const [volumeEnvelope, setVolumeEnvelope] = useState(DEFAULT_VOLUME_ENVELOPE)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [song, setSong] = useState<File | null>(null)
  const navigate = useNavigate()

  const voices = useVoices()
  const createCover = useCreateCover()

  const readyVoices = voices.data?.filter((voice) => voice.status === 'ready') ?? []
  const canSubmit = voiceId !== null && song !== null && !createCover.isPending

  const submit = () => {
    if (voiceId === null || song === null) return
    createCover.mutate(
      {
        voiceId,
        transpose: autoTranspose ? 0 : transpose,
        autoTranspose,
        vocalGain,
        indexRate,
        protect,
        volumeEnvelope,
        song,
      },
      {
        onSuccess: () => {
          toast.success('커버 생성을 시작했어요. 라이브러리에서 진행 상황을 볼 수 있어요.')
          void navigate('/library')
        },
        onError: (error) => toast.error(error.message),
      },
    )
  }

  return (
    <>
      <PageHeader
        title="커버 만들기"
        description="곡을 올리고 목소리를 고르면 분리 → 변환 → 믹싱까지 자동으로 진행돼요."
      />

      <StepCard step={1} title="곡 올리기">
        <SongDropzone file={song} onChange={setSong} />
      </StepCard>

      <StepCard step={2} title="목소리 고르기">
        {readyVoices.length === 0 ? (
          <p className="rounded-xl border border-dashed px-4 py-4 text-sm text-muted-foreground">
            사용 가능한 보이스가 없어요.{' '}
            <Link to="/voices" className="font-medium underline underline-offset-2">
              보이스를 먼저 학습시켜주세요.
            </Link>
          </p>
        ) : (
          <VoicePicker voices={readyVoices} selectedId={voiceId} onSelect={setVoiceId} />
        )}
      </StepCard>

      <StepCard step={3} title="세부 조정">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <Label>키 조절</Label>
            {!autoTranspose && (
              <span className="text-sm font-semibold text-primary tabular-nums">
                {formatTranspose(transpose)}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="키 조절 방식">
            <button
              type="button"
              role="radio"
              aria-checked={autoTranspose}
              onClick={() => setAutoTranspose(true)}
              className={cn(
                'rounded-xl border-2 px-3.5 py-2.5 text-left transition-all',
                autoTranspose
                  ? 'border-primary bg-accent'
                  : 'border-border bg-card hover:border-primary/40 hover:bg-muted/40',
              )}
            >
              <span className="block text-sm font-semibold">자동 맞춤 · 추천</span>
              <span className="block text-xs text-muted-foreground">
                목소리 음역에 맞춰 옥타브를 조절해요
              </span>
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={!autoTranspose}
              onClick={() => setAutoTranspose(false)}
              className={cn(
                'rounded-xl border-2 px-3.5 py-2.5 text-left transition-all',
                !autoTranspose
                  ? 'border-primary bg-accent'
                  : 'border-border bg-card hover:border-primary/40 hover:bg-muted/40',
              )}
            >
              <span className="block text-sm font-semibold">직접 조절</span>
              <span className="block text-xs text-muted-foreground">
                반음 단위로 원하는 키를 정해요
              </span>
            </button>
          </div>
          {autoTranspose ? (
            <p className="text-xs text-muted-foreground">
              곡의 보컬 음역과 학습한 목소리 음역을 비교해 자연스러운 옥타브(±12키)로 자동
              조절해요. 적용된 키는 완성 후 라이브러리에서 확인할 수 있어요.
            </p>
          ) : (
            <>
              <Slider
                min={-12}
                max={12}
                step={1}
                value={[transpose]}
                onValueChange={(values) => setTranspose(values[0] ?? 0)}
              />
              <p className="text-xs text-muted-foreground">
                남성 곡을 여성 보이스로 부르면 +12, 반대는 -12 근처가 자연스러워요.
              </p>
            </>
          )}
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <Label>보컬 볼륨</Label>
            <span className="text-sm font-semibold text-primary tabular-nums">
              {vocalGain.toFixed(1)}×
            </span>
          </div>
          <Slider
            min={0.5}
            max={2.5}
            step={0.1}
            value={[vocalGain]}
            onValueChange={(values) => setVocalGain(values[0] ?? DEFAULT_VOCAL_GAIN)}
          />
          <p className="text-xs text-muted-foreground">
            변환된 보컬이 반주에 묻히면 키우세요. 완성 후 라이브러리에서도 다시 조정할 수
            있어요.
          </p>
        </div>

        {/* 고급 설정: RVC 추론 품질 옵션 */}
        <div className="flex flex-col gap-4 rounded-xl border border-border/70 bg-muted/30 p-4">
          <button
            type="button"
            onClick={() => setShowAdvanced((prev) => !prev)}
            className="flex items-center justify-between text-left"
            aria-expanded={showAdvanced}
          >
            <span className="flex flex-col">
              <span className="text-sm font-semibold">고급 설정 · 변환 품질</span>
              <span className="text-xs text-muted-foreground">
                결과가 아쉬울 때 미세 조정하세요. 기본값으로도 잘 동작해요.
              </span>
            </span>
            <ChevronDown
              className={cn(
                'size-5 shrink-0 text-muted-foreground transition-transform',
                showAdvanced && 'rotate-180',
              )}
            />
          </button>

          {showAdvanced && (
            <div className="flex flex-col gap-5 border-t border-border/70 pt-4">
              <OptionSlider
                label="음색 반영"
                tip="학습한 목소리 특징을 얼마나 강하게 입힐지 정해요. 높이면 음색이 더 뚜렷해지지만 잡음이 늘 수 있고, 낮추면 원 발음이 또렷해집니다. (기본 0.50)"
                value={indexRate}
                display={indexRate.toFixed(2)}
                min={0}
                max={1}
                step={0.05}
                onChange={setIndexRate}
              />
              <OptionSlider
                label="자음·숨소리 보호"
                tip="자음과 숨소리를 보호해 발음이 뭉개지는 걸 막아요. 값이 높을수록(최대 0.50) 보호가 강해지지만 음색 반영은 약해질 수 있어요. (기본 0.33)"
                value={protect}
                display={protect.toFixed(2)}
                min={0}
                max={0.5}
                step={0.01}
                onChange={setProtect}
              />
              <OptionSlider
                label="볼륨 곡선 반영"
                tip="원곡 보컬의 강약(볼륨 흐름)을 얼마나 따라갈지 정해요. 1이면 변환된 목소리 기준, 낮추면 원곡의 다이내믹을 더 살립니다. (기본 1.00)"
                value={volumeEnvelope}
                display={volumeEnvelope.toFixed(2)}
                min={0}
                max={1}
                step={0.05}
                onChange={setVolumeEnvelope}
              />
            </div>
          )}
        </div>
      </StepCard>

      <div className="flex items-center gap-4">
        <Button size="lg" onClick={submit} disabled={!canSubmit} className="px-6">
          <Sparkles className="size-4" />
          {createCover.isPending ? '시작하는 중…' : '커버 만들기'}
        </Button>
        {!canSubmit && !createCover.isPending && (
          <p className="text-sm text-muted-foreground">
            {song === null ? '곡을 올려주세요.' : voiceId === null ? '목소리를 골라주세요.' : ''}
          </p>
        )}
      </div>
    </>
  )
}
