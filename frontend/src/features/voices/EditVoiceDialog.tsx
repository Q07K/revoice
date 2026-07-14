import { Pencil } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import type { Voice } from '@/api/types'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useUpdateVoice } from '@/features/voices/queries'

export function EditVoiceDialog({ voice }: { voice: Voice }) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(voice.name)
  const [description, setDescription] = useState(voice.description)
  const update = useUpdateVoice(voice.id)

  const openDialog = () => {
    // 닫았다 다시 열면 항상 현재 값에서 시작한다.
    setName(voice.name)
    setDescription(voice.description)
    setOpen(true)
  }

  const submit = () => {
    const trimmed = name.trim()
    if (trimmed.length === 0) {
      toast.error('이름을 입력해주세요.')
      return
    }
    update.mutate(
      { name: trimmed, description: description.trim() },
      {
        onSuccess: () => {
          toast.success('보이스 정보를 수정했어요.')
          setOpen(false)
        },
        onError: (error) => toast.error(error.message),
      },
    )
  }

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        onClick={openDialog}
        aria-label="이름·설명 수정"
        className="text-muted-foreground hover:text-foreground"
      >
        <Pencil className="size-4" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>보이스 정보 수정</DialogTitle>
            <DialogDescription>
              이름과 설명만 바뀌어요. 학습된 모델과 커버에는 영향이 없습니다.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="voice-name">이름</Label>
              <Input
                id="voice-name"
                value={name}
                maxLength={100}
                onChange={(event) => setName(event.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="voice-description">설명</Label>
              <Textarea
                id="voice-description"
                value={description}
                maxLength={2000}
                rows={3}
                placeholder="예: 발라드용, 2절까지 녹음한 데이터셋"
                onChange={(event) => setDescription(event.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              취소
            </Button>
            <Button onClick={submit} disabled={update.isPending}>
              {update.isPending ? '저장 중…' : '저장'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
