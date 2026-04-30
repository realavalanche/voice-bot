import { useState, useRef, useCallback } from 'react'

export type RecorderState = 'idle' | 'recording' | 'processing'

const SILENCE_THRESHOLD = 0.015   // RMS amplitude — raise if too hair-trigger
const SILENCE_DURATION_MS = 1500  // 1.5s of quiet → auto-stop
const MIN_RECORD_MS = 500         // ignore silence in first 500ms

export function useVoiceRecorder() {
  const [state, setState] = useState<RecorderState>('idle')
  const [error, setError] = useState<string | null>(null)

  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const onCompleteRef = useRef<((blob: Blob) => void) | null>(null)
  const silenceIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const recordStartRef = useRef<number>(0)

  const stopInternal = useCallback(() => {
    const recorder = mediaRef.current
    if (!recorder || recorder.state === 'inactive') return
    if (silenceIntervalRef.current) clearInterval(silenceIntervalRef.current)
    audioCtxRef.current?.close()
    setState('processing')
    recorder.stop()
  }, [])

  const start = useCallback(
    async (onComplete: (blob: Blob) => void) => {
      setError(null)
      onCompleteRef.current = onComplete

      let stream: MediaStream
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      } catch {
        setError('Microphone access denied')
        return
      }

      const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : ''
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      chunksRef.current = []
      recordStartRef.current = Date.now()

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        })
        stream.getTracks().forEach((t) => t.stop())
        setState('idle')
        onCompleteRef.current?.(blob)
      }

      mediaRef.current = recorder
      recorder.start(100)
      setState('recording')

      // Voice Activity Detection via Web Audio AnalyserNode
      try {
        const audioCtx = new AudioContext()
        const analyser = audioCtx.createAnalyser()
        analyser.fftSize = 1024
        audioCtx.createMediaStreamSource(stream).connect(analyser)
        audioCtxRef.current = audioCtx

        const buf = new Float32Array(analyser.fftSize)
        let silenceStart: number | null = null

        silenceIntervalRef.current = setInterval(() => {
          if (mediaRef.current?.state !== 'recording') return
          if (Date.now() - recordStartRef.current < MIN_RECORD_MS) return

          analyser.getFloatTimeDomainData(buf)
          const rms = Math.sqrt(buf.reduce((s, v) => s + v * v, 0) / buf.length)

          if (rms < SILENCE_THRESHOLD) {
            silenceStart ??= Date.now()
            if (Date.now() - silenceStart > SILENCE_DURATION_MS) {
              clearInterval(silenceIntervalRef.current!)
              stopInternal()
            }
          } else {
            silenceStart = null
          }
        }, 100)
      } catch {
        // VAD unavailable — manual stop only
      }
    },
    [stopInternal]
  )

  // Manual stop — user taps button mid-speech
  const stop = useCallback(() => {
    if (silenceIntervalRef.current) clearInterval(silenceIntervalRef.current)
    stopInternal()
  }, [stopInternal])

  return { state, error, start, stop }
}
