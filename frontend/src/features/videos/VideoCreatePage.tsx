import { ArrowLeft, Check, Copy, Download, Film, Image as ImageIcon, Upload } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { videoDownloadUrl } from '@/api/videos'
import type { CoverJob, VideoAspect, VideoJob, VideoVisual } from '@/api/types'
import { PageHeader } from '@/components/shared/PageHeader'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { useCovers } from '@/features/covers/queries'
import { useVoices } from '@/features/voices/queries'
import {
  isVideoInProgress,
  useCoverVideos,
  useCreateVideo,
  useDeleteVideo,
} from '@/features/videos/queries'
import { cn } from '@/lib/utils'
import { formatDuration, formatTranspose } from '@/lib/format'

const VISUALS: { key: VideoVisual; label: string }[] = [
  { key: 'image', label: '커버 이미지' },
  { key: 'wave', label: '파형' },
  { key: 'spectrum', label: '스펙트럼' },
]
const ASPECTS: { key: VideoAspect; label: string }[] = [
  { key: '16:9', label: '16:9 일반' },
  { key: '9:16', label: '9:16 Shorts' },
]
const TABS = [
  { key: 'visual', label: '비주얼' },
  { key: 'text', label: '텍스트' },
  { key: 'export', label: '내보내기' },
] as const
type TabKey = (typeof TABS)[number]['key']

const BARS = Array.from({ length: 40 }, (_, i) => 24 + Math.round(60 * Math.abs(Math.sin(i * 1.7))))

function PreviewFrame({
  visual,
  aspect,
  title,
  subtitle,
  imageUrl,
}: {
  visual: VideoVisual
  aspect: VideoAspect
  title: string
  subtitle: string
  imageUrl: string | null
}) {
  return (
    <div className="grid place-items-center rounded-xl bg-muted/40 p-4">
      <div
        className={cn(
          'relative overflow-hidden rounded-lg shadow-lg',
          aspect === '16:9' ? 'aspect-video w-full' : 'aspect-[9/16] h-[380px] max-h-[60vh]',
        )}
        style={{ background: '#12242b' }}
      >
        {visual === 'image' &&
          (imageUrl ? (
            <img src={imageUrl} alt="" className="absolute inset-0 size-full object-cover" />
          ) : (
            <div
              className="absolute inset-0"
              style={{
                background:
                  'radial-gradient(120% 120% at 30% 20%, #3a5560, #182126), linear-gradient(135deg, rgba(185,160,106,.2), rgba(127,174,156,.13))',
              }}
            >
              <div className="grid size-full place-items-center">
                <div
                  className="aspect-square w-[44%] rounded-full"
                  style={{
                    background: 'conic-gradient(#26424c, #0e1a1f, #26424c)',
                    boxShadow: 'inset 0 0 0 15% #0e1a1f, inset 0 0 0 16% rgba(255,255,255,.15)',
                  }}
                />
              </div>
            </div>
          ))}
        {visual === 'wave' && (
          <div className="absolute inset-x-0 bottom-[22%] flex h-[34%] items-center justify-center gap-[3px] px-[8%]">
            {BARS.map((h, i) => (
              <span
                key={i}
                className="flex-1 rounded-sm"
                style={{
                  height: `${h}%`,
                  background: 'linear-gradient(180deg, #7fd0d8, #2f8f99)',
                }}
              />
            ))}
          </div>
        )}
        {visual === 'spectrum' && (
          <div className="absolute inset-0 grid grid-cols-[repeat(24,1fr)] items-end gap-[2px] px-[6%] pb-[16%] pt-[14%]">
            {Array.from({ length: 24 }).map((_, i) => (
              <span
                key={i}
                className="rounded-[1px]"
                style={{
                  height: `${30 + Math.round(60 * Math.abs(Math.sin(i * 0.9)))}%`,
                  background: 'linear-gradient(180deg, #e0a33a, #16626b)',
                  opacity: 0.85,
                }}
              />
            ))}
          </div>
        )}
        <span className="absolute right-[6%] top-[5%] text-[10px] font-extrabold tracking-wide text-white/80">
          REVOICE
        </span>
        {aspect === '9:16' && (
          <span className="absolute left-[6%] top-[5%] rounded-md bg-[#e0344c] px-2 py-0.5 text-[9px] font-extrabold text-white">
            SHORTS
          </span>
        )}
        <div
          className="absolute inset-x-0 bottom-0 px-[7%] pb-[8%] pt-[18%]"
          style={{ background: 'linear-gradient(180deg, transparent, rgba(0,0,0,.6))' }}
        >
          <p className="m-0 font-extrabold leading-tight text-white [text-shadow:0_2px_8px_rgba(0,0,0,.5)] text-[clamp(15px,2.4vw,26px)]">
            {title || '제목'}
          </p>
          {subtitle && (
            <span className="mt-2 inline-block rounded-full bg-[#7fd0d8] px-2 py-0.5 text-[clamp(9px,1.4vw,13px)] font-bold text-[#0c2f33]">
              {subtitle}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: { key: T; label: string }[]
  onChange: (value: T) => void
}) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-xl bg-muted p-1">
      {options.map((opt) => (
        <button
          key={opt.key}
          type="button"
          onClick={() => onChange(opt.key)}
          className={cn(
            'rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors',
            value === opt.key
              ? 'bg-card text-primary shadow-sm'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

function RenderedVideo({ job, coverId }: { job: VideoJob; coverId: number }) {
  const deleteVideo = useDeleteVideo(coverId)
  const url = videoDownloadUrl(job.id, job.finished_at)
  if (isVideoInProgress(job)) {
    return (
      <div className="flex flex-col gap-1.5 rounded-lg border bg-card p-3">
        <Progress value={job.progress * 100} />
        <div className="flex justify-between text-xs text-muted-foreground tabular-nums">
          <span>영상 렌더링 중…</span>
          <span>
            {job.eta_seconds !== null ? `약 ${formatDuration(job.eta_seconds)} 남음` : '계산 중…'}
          </span>
        </div>
      </div>
    )
  }
  if (job.status === 'failed') {
    return (
      <div className="flex items-center justify-between gap-2 rounded-lg border bg-card p-3">
        <span className="text-sm text-status-failed">{job.error ?? '렌더링 실패'}</span>
        <Button variant="ghost" size="sm" onClick={() => deleteVideo.mutate(job.id)}>
          삭제
        </Button>
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-card p-3">
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video controls preload="none" src={url} className="w-full rounded-md" />
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">
          {job.visual} · {job.aspect} · mp4
        </span>
        <span className="flex gap-1">
          <a href={url} download>
            <Button variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-xs">
              <Download className="size-3.5" />
              내려받기
            </Button>
          </a>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-muted-foreground hover:text-status-failed"
            onClick={() => deleteVideo.mutate(job.id)}
          >
            삭제
          </Button>
        </span>
      </div>
    </div>
  )
}

export function VideoCreatePage() {
  const { coverId: coverIdParam } = useParams()
  const coverId = Number(coverIdParam)
  const navigate = useNavigate()

  const covers = useCovers()
  const voices = useVoices()
  const cover: CoverJob | undefined = covers.data?.find((c) => c.id === coverId)
  const voiceName = voices.data?.find((v) => v.id === cover?.voice_id)?.name

  const [visual, setVisual] = useState<VideoVisual>('wave')
  const [aspect, setAspect] = useState<VideoAspect>('16:9')
  const [title, setTitle] = useState('')
  const [subtitle, setSubtitle] = useState('')
  const [image, setImage] = useState<File | null>(null)
  const [tab, setTab] = useState<TabKey>('visual')
  const [copied, setCopied] = useState(false)
  const [primed, setPrimed] = useState(false)

  const createVideo = useCreateVideo(coverId)
  const videos = useCoverVideos(coverId)

  // seed title/subtitle from the cover once it loads
  useEffect(() => {
    if (cover && !primed) {
      setTitle(cover.title.replace(/\.[^.]+$/, ''))
      const key = formatTranspose(cover.transpose)
      setSubtitle(`${voiceName ?? '커버'} AI 커버 · ${key}`)
      setPrimed(true)
    }
  }, [cover, voiceName, primed])

  const imageUrl = useMemo(() => (image ? URL.createObjectURL(image) : null), [image])
  useEffect(() => () => {
    if (imageUrl) URL.revokeObjectURL(imageUrl)
  }, [imageUrl])

  const description = useMemo(() => {
    const key = cover ? formatTranspose(cover.transpose) : ''
    return [
      `${title} (${voiceName ?? '보이스'} AI 커버)`,
      '',
      `원곡: ${title}`,
      `AI 보이스: ${voiceName ?? '-'}`,
      `키: ${key}`,
      'Revoice로 제작',
    ].join('\n')
  }, [title, voiceName, cover])

  const copyDescription = async () => {
    try {
      await navigator.clipboard.writeText(description)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      toast.error('복사에 실패했어요. 직접 선택해 복사해주세요.')
    }
  }

  const submit = () => {
    createVideo.mutate(
      { coverId, title, subtitle, visual, aspect, image },
      {
        onSuccess: () => toast.success('영상 렌더링을 시작했어요. 아래에서 진행 상황을 볼 수 있어요.'),
        onError: (error) => toast.error(error.message),
      },
    )
  }

  if (covers.isLoading) {
    return <PageHeader title="영상 만들기" description="커버 정보를 불러오는 중…" />
  }
  if (!cover || cover.status !== 'completed') {
    return (
      <>
        <PageHeader title="영상 만들기" description="완성된 커버에서만 영상을 만들 수 있어요." />
        <Button variant="secondary" onClick={() => navigate('/library')}>
          <ArrowLeft className="size-4" />
          라이브러리로
        </Button>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="영상 만들기"
        description={`'${cover.title}' · ${voiceName ?? ''} 커버를 유튜브용 mp4로 만듭니다.`}
      />
      <div className="flex flex-col gap-5">
        <PreviewFrame
          visual={visual}
          aspect={aspect}
          title={title}
          subtitle={subtitle}
          imageUrl={imageUrl}
        />

        <div className="flex items-center justify-between gap-3">
          <Segmented value={tab} options={TABS as unknown as { key: TabKey; label: string }[]} onChange={setTab} />
          <Segmented value={aspect} options={ASPECTS} onChange={setAspect} />
        </div>

        <Card>
          <CardContent className="flex flex-col gap-5 pt-6">
            {tab === 'visual' && (
              <>
                <div className="flex flex-col gap-2">
                  <Label>비주얼 스타일</Label>
                  <Segmented value={visual} options={VISUALS} onChange={setVisual} />
                </div>
                {visual === 'image' && (
                  <div className="flex flex-col gap-2">
                    <Label>커버 이미지</Label>
                    <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed bg-muted/40 px-4 py-4 transition-colors hover:bg-muted">
                      {image ? (
                        <ImageIcon className="size-5 text-primary" />
                      ) : (
                        <Upload className="size-5 text-muted-foreground" />
                      )}
                      <span className="text-sm text-muted-foreground">
                        {image ? image.name : '이미지 업로드 (jpg · png · webp) — 없으면 자동 아트'}
                      </span>
                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png,.webp"
                        className="hidden"
                        onChange={(e) => setImage(e.target.files?.[0] ?? null)}
                      />
                    </label>
                  </div>
                )}
                <p className="text-xs text-muted-foreground">
                  비율은 오른쪽 위에서 16:9(일반) / 9:16(Shorts)로 바꿀 수 있어요.
                </p>
              </>
            )}

            {tab === 'text' && (
              <>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="v-title">제목</Label>
                  <Input id="v-title" value={title} onChange={(e) => setTitle(e.target.value)} />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="v-sub">부제</Label>
                  <Input id="v-sub" value={subtitle} onChange={(e) => setSubtitle(e.target.value)} />
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <Label>유튜브 설명문 초안</Label>
                    <Button variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-xs" onClick={copyDescription}>
                      {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                      {copied ? '복사됨' : '복사'}
                    </Button>
                  </div>
                  <pre className="whitespace-pre-wrap rounded-lg border bg-muted/40 p-3 text-xs text-foreground">
                    {description}
                  </pre>
                </div>
              </>
            )}

            {tab === 'export' && (
              <>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-muted-foreground">
                    {aspect === '16:9' ? '1920×1080' : '1080×1920'} · {visual} · mp4 (H.264/AAC)
                  </span>
                  <Button onClick={submit} disabled={createVideo.isPending}>
                    <Film className="size-4" />
                    {createVideo.isPending ? '시작하는 중…' : '영상 내보내기'}
                  </Button>
                </div>
                <div className="flex flex-col gap-2">
                  {(videos.data ?? []).length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      아직 만든 영상이 없어요. 위 버튼으로 첫 영상을 렌더링해보세요.
                    </p>
                  ) : (
                    (videos.data ?? []).map((job) => (
                      <RenderedVideo key={job.id} job={job} coverId={coverId} />
                    ))
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Link to="/library" className="text-sm text-muted-foreground hover:text-foreground">
          ← 라이브러리로 돌아가기
        </Link>
      </div>
    </>
  )
}
