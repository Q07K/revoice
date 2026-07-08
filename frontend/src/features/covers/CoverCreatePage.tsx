import { Music2, Sparkles, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { useCreateCover } from '@/features/covers/queries'
import { useVoices } from '@/features/voices/queries'
import { formatBytes, formatTranspose } from '@/lib/format'

export function CoverCreatePage() {
  const [voiceId, setVoiceId] = useState<number | null>(null)
  const [transpose, setTranspose] = useState(0)
  const [song, setSong] = useState<File | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const voices = useVoices()
  const createCover = useCreateCover()

  const readyVoices = voices.data?.filter((voice) => voice.status === 'ready') ?? []
  const canSubmit = voiceId !== null && song !== null && !createCover.isPending

  const submit = () => {
    if (voiceId === null || song === null) return
    createCover.mutate(
      { voiceId, transpose, song },
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
        description="곡을 올리면 보컬을 분리해 선택한 보이스로 다시 부르고, 반주와 믹싱합니다."
      />
      <Card>
        <CardHeader>
          <CardTitle>새 커버</CardTitle>
          <CardDescription>
            분리 → 변환 → 믹싱까지 자동으로 진행돼요. 곡 길이에 따라 몇 분 걸릴 수 있습니다.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <Label>보이스 선택</Label>
            {readyVoices.length === 0 ? (
              <p className="rounded-xl border border-dashed px-4 py-4 text-sm text-muted-foreground">
                사용 가능한 보이스가 없어요.{' '}
                <Link to="/voices" className="font-medium underline underline-offset-2">
                  보이스를 먼저 학습시켜주세요.
                </Link>
              </p>
            ) : (
              <Select
                value={voiceId === null ? undefined : String(voiceId)}
                onValueChange={(value) => setVoiceId(Number(value))}
              >
                <SelectTrigger className="w-full sm:w-80">
                  <SelectValue placeholder="학습이 끝난 보이스 중에서 선택" />
                </SelectTrigger>
                <SelectContent>
                  {readyVoices.map((voice) => (
                    <SelectItem key={voice.id} value={String(voice.id)}>
                      {voice.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label>원곡 파일</Label>
            <input
              ref={inputRef}
              type="file"
              accept=".wav,.mp3,.flac,.m4a,.ogg"
              className="hidden"
              onChange={(event) => setSong(event.target.files?.[0] ?? null)}
            />
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="flex items-center gap-3 rounded-xl border border-dashed bg-muted/40 px-4 py-5 text-left transition-colors hover:bg-muted"
            >
              {song === null ? (
                <>
                  <Upload className="size-5 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    클릭해서 곡 파일 선택 (wav · mp3 · flac · m4a · ogg)
                  </span>
                </>
              ) : (
                <>
                  <Music2 className="size-5 text-primary" />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">{song.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatBytes(song.size)} · 다시 클릭하면 변경
                    </span>
                  </span>
                </>
              )}
            </button>
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <Label>키 조절</Label>
              <span className="text-sm font-semibold text-primary tabular-nums">
                {formatTranspose(transpose)}
              </span>
            </div>
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
          </div>

          <Button size="lg" onClick={submit} disabled={!canSubmit} className="w-fit">
            <Sparkles className="size-4" />
            {createCover.isPending ? '시작하는 중…' : '커버 만들기'}
          </Button>
        </CardContent>
      </Card>
    </>
  )
}
