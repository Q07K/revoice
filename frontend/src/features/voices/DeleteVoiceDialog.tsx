import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import type { VoiceDetail } from '@/api/types'
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
import { useDeleteVoice } from '@/features/voices/queries'

export function DeleteVoiceDialog({ voice }: { voice: VoiceDetail }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const deleteVoice = useDeleteVoice()

  const submit = () => {
    deleteVoice.mutate(voice.id, {
      onSuccess: () => {
        toast.success(`'${voice.name}' 보이스를 삭제했어요.`)
        void navigate('/voices')
      },
      onError: (error) => toast.error(error.message),
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="보이스 삭제">
          <Trash2 className="size-4 text-muted-foreground" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>보이스 삭제</DialogTitle>
          <DialogDescription>
            '{voice.name}' 보이스와 데이터셋 {voice.dataset_files.length}개, 학습된 모델이
            함께 삭제됩니다. 되돌릴 수 없어요.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="secondary" onClick={() => setOpen(false)}>
            취소
          </Button>
          <Button variant="destructive" onClick={submit} disabled={deleteVoice.isPending}>
            {deleteVoice.isPending ? '삭제 중…' : '삭제'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
