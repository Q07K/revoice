import { useEffect, useRef, useState } from 'react'

export interface AudioPlayer {
  playing: boolean
  /** 재생 위치 (0~1). 재생 전/종료 후에는 0. */
  progress: number
  toggle: () => void
  seek: (fraction: number) => void
}

/** 커버 오디오 하나를 재생/시킹하고 진행 위치를 상태로 노출한다. */
export function useAudioPlayer(src: string): AudioPlayer {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    return () => audioRef.current?.pause()
  }, [])

  const ensureAudio = (): HTMLAudioElement => {
    if (audioRef.current === null) {
      const audio = new Audio(src)
      audio.preload = 'metadata'
      audio.ontimeupdate = () => {
        if (audio.duration > 0) setProgress(audio.currentTime / audio.duration)
      }
      audio.onplay = () => setPlaying(true)
      audio.onpause = () => setPlaying(false)
      audio.onended = () => {
        setPlaying(false)
        setProgress(0)
      }
      audioRef.current = audio
    }
    return audioRef.current
  }

  const toggle = () => {
    const audio = ensureAudio()
    if (audio.paused) void audio.play()
    else audio.pause()
  }

  const seek = (fraction: number) => {
    const audio = ensureAudio()
    const clamped = Math.min(Math.max(fraction, 0), 1)
    const apply = () => {
      if (Number.isFinite(audio.duration) && audio.duration > 0) {
        audio.currentTime = clamped * audio.duration
        setProgress(clamped)
        if (audio.paused) void audio.play()
      }
    }
    if (Number.isFinite(audio.duration) && audio.duration > 0) {
      apply()
    } else {
      audio.onloadedmetadata = apply
      audio.load()
    }
  }

  return { playing, progress, toggle, seek }
}
