import { FileAudio, Upload } from 'lucide-react'
import { useRef } from 'react'
import { toast } from 'sonner'

import type { VoiceDetail } from '@/api/types'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useUploadDataset } from '@/features/voices/queries'
import { formatBytes, formatDate } from '@/lib/format'

export function DatasetCard({ voice }: { voice: VoiceDetail }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const upload = useUploadDataset(voice.id)
  const isTraining = voice.status === 'training'

  const handleFiles = (fileList: FileList | null) => {
    if (fileList === null || fileList.length === 0) return
    upload.mutate(Array.from(fileList), {
      onSuccess: (files) => toast.success(`오디오 ${files.length}개를 올렸어요.`),
      onError: (error) => toast.error(error.message),
    })
    if (inputRef.current !== null) inputRef.current.value = ''
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>학습 데이터셋</CardTitle>
            <CardDescription>
              반주나 배경음은 학습 전에 자동으로 정리돼요. 한 사람 목소리만 담긴 파일로
              30분 이상을 권장합니다.
            </CardDescription>
          </div>
          <Button
            variant="secondary"
            onClick={() => inputRef.current?.click()}
            disabled={isTraining || upload.isPending}
          >
            <Upload className="size-4" />
            {upload.isPending ? '올리는 중…' : '오디오 추가'}
          </Button>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".wav,.mp3,.flac,.m4a,.ogg"
          multiple
          className="hidden"
          onChange={(event) => handleFiles(event.target.files)}
        />
      </CardHeader>
      <CardContent>
        {voice.dataset_files.length === 0 ? (
          <p className="rounded-xl border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">
            아직 올린 오디오가 없어요. wav · mp3 · flac · m4a · ogg 파일을 올릴 수 있습니다.
          </p>
        ) : (
          <ul className="divide-y">
            {voice.dataset_files.map((file) => (
              <li key={file.id} className="flex items-center gap-3 py-2.5">
                <FileAudio className="size-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1 truncate text-sm">{file.original_name}</span>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {formatBytes(file.size_bytes)}
                </span>
                <span className="text-xs text-muted-foreground">
                  {formatDate(file.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
