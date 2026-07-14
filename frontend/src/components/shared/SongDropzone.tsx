import { Music2, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import type { DragEvent } from 'react'

import { cn } from '@/lib/utils'
import { formatBytes } from '@/lib/format'

const ACCEPT = '.wav,.mp3,.flac,.m4a,.ogg'
const ACCEPT_EXTENSIONS = ACCEPT.split(',')

interface SongDropzoneProps {
  file: File | null
  onChange: (file: File | null) => void
}

export function SongDropzone({ file, onChange }: SongDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const pickDropped = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    const dropped = event.dataTransfer.files[0]
    if (dropped === undefined) return
    const name = dropped.name.toLowerCase()
    if (!ACCEPT_EXTENSIONS.some((extension) => name.endsWith(extension))) return
    onChange(dropped)
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={pickDropped}
        className={cn(
          'flex flex-col items-center gap-2 rounded-2xl border-2 border-dashed px-6 py-8 text-center transition-colors',
          dragging
            ? 'border-primary bg-accent'
            : 'border-border bg-muted/40 hover:border-primary/40 hover:bg-muted',
        )}
      >
        {file === null ? (
          <>
            <span className="flex size-11 items-center justify-center rounded-full bg-background text-muted-foreground shadow-sm">
              <Upload className="size-5" />
            </span>
            <span className="text-sm font-medium">
              곡 파일을 끌어다 놓거나 클릭해서 선택
            </span>
            <span className="text-xs text-muted-foreground">
              wav · mp3 · flac · m4a · ogg
            </span>
          </>
        ) : (
          <>
            <span className="flex size-11 items-center justify-center rounded-full bg-accent text-accent-foreground">
              <Music2 className="size-5" />
            </span>
            <span className="max-w-full truncate text-sm font-semibold">{file.name}</span>
            <span className="text-xs text-muted-foreground">
              {formatBytes(file.size)} · 다시 클릭하면 변경
            </span>
          </>
        )}
      </button>
    </>
  )
}
