import { useCallback, useEffect, useRef, useState } from 'react'

import { coverStemUrl } from '@/api/covers'

export type StemKind = 'vocal' | 'instrumental'

export interface TrackState {
  volume: number
  muted: boolean
  solo: boolean
}

const TRACK_KEYS: StemKind[] = ['vocal', 'instrumental']

interface Nodes {
  gain: Record<StemKind, GainNode>
  buffers: Record<StemKind, AudioBuffer>
  sources: Partial<Record<StemKind, AudioBufferSourceNode>>
}

const initialTracks: Record<StemKind, TrackState> = {
  vocal: { volume: 1.5, muted: false, solo: false },
  instrumental: { volume: 1, muted: false, solo: false },
}

/**
 * Loads a cover's two stems and plays them in perfect sync via the Web Audio
 * API. Volume / mute / solo are applied live on gain nodes — no server round
 * trip — which is what makes the studio feel like an editor rather than a form.
 */
export function useMultitrack(coverId: number) {
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [isPlaying, setPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [tracks, setTracks] = useState<Record<StemKind, TrackState>>(initialTracks)

  const ctxRef = useRef<AudioContext | null>(null)
  const nodesRef = useRef<Nodes | null>(null)
  const masterRef = useRef<GainNode | null>(null)
  const offsetRef = useRef(0) // playback position when stopped
  const startedAtRef = useRef(0) // ctx time when current play began
  const tracksRef = useRef(tracks)
  tracksRef.current = tracks

  const positionRef = useRef(0)
  const getPosition = useCallback(() => {
    const ctx = ctxRef.current
    if (isPlaying && ctx) return Math.min(ctx.currentTime - startedAtRef.current, duration)
    return offsetRef.current
  }, [isPlaying, duration])

  const applyGains = useCallback((state: Record<StemKind, TrackState>) => {
    const nodes = nodesRef.current
    const ctx = ctxRef.current
    if (!nodes || !ctx) return
    const soloActive = TRACK_KEYS.some((k) => state[k].solo)
    for (const kind of TRACK_KEYS) {
      const t = state[kind]
      const audible = soloActive ? t.solo : !t.muted
      nodes.gain[kind].gain.setTargetAtTime(audible ? t.volume : 0, ctx.currentTime, 0.02)
    }
  }, [])

  // ---- load + decode both stems ----
  useEffect(() => {
    let cancelled = false
    const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()
    ctxRef.current = ctx
    const master = ctx.createGain()
    master.connect(ctx.destination)
    masterRef.current = master

    async function load() {
      try {
        const entries = await Promise.all(
          TRACK_KEYS.map(async (kind) => {
            const res = await fetch(coverStemUrl(coverId, kind))
            if (!res.ok) throw new Error(`${kind} 트랙을 불러오지 못했어요.`)
            const buf = await ctx.decodeAudioData(await res.arrayBuffer())
            return [kind, buf] as const
          }),
        )
        if (cancelled) return
        const buffers = Object.fromEntries(entries) as Record<StemKind, AudioBuffer>
        const gain = Object.fromEntries(
          TRACK_KEYS.map((kind) => {
            const g = ctx.createGain()
            g.connect(master)
            return [kind, g]
          }),
        ) as Record<StemKind, GainNode>
        nodesRef.current = { gain, buffers, sources: {} }
        setDuration(Math.max(...TRACK_KEYS.map((k) => buffers[k].duration)))
        applyGains(initialTracks)
        setStatus('ready')
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '트랙 로딩 실패')
          setStatus('error')
        }
      }
    }
    void load()

    return () => {
      cancelled = true
      void ctx.close()
    }
  }, [coverId, applyGains])

  const stopSources = useCallback(() => {
    const nodes = nodesRef.current
    if (!nodes) return
    for (const kind of TRACK_KEYS) {
      const src = nodes.sources[kind]
      if (src) {
        try {
          src.onended = null
          src.stop()
        } catch {
          /* already stopped */
        }
      }
    }
    nodes.sources = {}
  }, [])

  const startFrom = useCallback(
    (offset: number) => {
      const ctx = ctxRef.current
      const nodes = nodesRef.current
      if (!ctx || !nodes) return
      stopSources()
      for (const kind of TRACK_KEYS) {
        const src = ctx.createBufferSource()
        src.buffer = nodes.buffers[kind]
        src.connect(nodes.gain[kind])
        src.start(0, Math.min(offset, nodes.buffers[kind].duration))
        nodes.sources[kind] = src
      }
      startedAtRef.current = ctx.currentTime - offset
      const endSrc = nodes.sources.vocal ?? nodes.sources.instrumental
      if (endSrc) {
        endSrc.onended = () => {
          // only treat as natural end if we reached the tail
          if (ctxRef.current && ctxRef.current.currentTime - startedAtRef.current >= duration - 0.05) {
            offsetRef.current = 0
            setPlaying(false)
          }
        }
      }
    },
    [duration, stopSources],
  )

  const play = useCallback(async () => {
    const ctx = ctxRef.current
    if (!ctx || status !== 'ready') return
    if (ctx.state === 'suspended') await ctx.resume()
    const from = offsetRef.current >= duration ? 0 : offsetRef.current
    startFrom(from)
    setPlaying(true)
  }, [status, duration, startFrom])

  const pause = useCallback(() => {
    offsetRef.current = getPosition()
    stopSources()
    setPlaying(false)
  }, [getPosition, stopSources])

  const toggle = useCallback(() => {
    if (isPlaying) pause()
    else void play()
  }, [isPlaying, pause, play])

  const seek = useCallback(
    (time: number) => {
      const clamped = Math.max(0, Math.min(time, duration))
      offsetRef.current = clamped
      positionRef.current = clamped
      if (isPlaying) startFrom(clamped)
    },
    [duration, isPlaying, startFrom],
  )

  const update = useCallback(
    (kind: StemKind, patch: Partial<TrackState>) => {
      setTracks((prev) => {
        const next = { ...prev, [kind]: { ...prev[kind], ...patch } }
        applyGains(next)
        return next
      })
    },
    [applyGains],
  )

  const setVolume = useCallback((kind: StemKind, volume: number) => update(kind, { volume }), [update])
  const toggleMute = useCallback(
    (kind: StemKind) => update(kind, { muted: !tracksRef.current[kind].muted }),
    [update],
  )
  const toggleSolo = useCallback(
    (kind: StemKind) => update(kind, { solo: !tracksRef.current[kind].solo }),
    [update],
  )

  const bufferOf = useCallback((kind: StemKind) => nodesRef.current?.buffers[kind] ?? null, [])

  return {
    status,
    error,
    isPlaying,
    duration,
    tracks,
    getPosition,
    positionRef,
    toggle,
    play,
    pause,
    seek,
    setVolume,
    toggleMute,
    toggleSolo,
    bufferOf,
  }
}
