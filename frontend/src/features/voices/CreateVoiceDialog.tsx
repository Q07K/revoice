import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useCreateVoice } from '@/features/voices/queries'

export function CreateVoiceDialog() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const navigate = useNavigate()
  const createVoice = useCreateVoice()

  const submit = () => {
    createVoice.mutate(
      { name: name.trim(), description: description.trim() },
      {
        onSuccess: (voice) => {
          toast.success(`'${voice.name}' 보이스를 만들었어요. 데이터셋을 올려주세요.`)
          setOpen(false)
          setName('')
          setDescription('')
          void navigate(`/voices/${voice.id}`)
        },
        onError: (error) => toast.error(error.message),
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="size-4" /> 새 보이스
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>새 보이스 모델</DialogTitle>
          <DialogDescription>
            학습할 목소리의 이름을 정해주세요. 생성 후 데이터셋 오디오를 올리고 학습을
            시작합니다.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="voice-name">이름</Label>
            <Input
              id="voice-name"
              placeholder="예: 루나 · 여성 보컬"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="voice-description">설명 (선택)</Label>
            <Textarea
              id="voice-description"
              placeholder="목소리 특징, 데이터 출처 등을 메모해두세요."
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            onClick={submit}
            disabled={name.trim().length === 0 || createVoice.isPending}
          >
            {createVoice.isPending ? '만드는 중…' : '보이스 만들기'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
