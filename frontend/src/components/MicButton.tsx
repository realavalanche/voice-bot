import { Mic, Loader2, Square } from 'lucide-react'
import clsx from 'clsx'

interface Props {
  state: 'idle' | 'recording' | 'processing'
  onStart: () => void
  onStop: () => void
}

export function MicButton({ state, onStart, onStop }: Props) {
  const isRecording = state === 'recording'
  const isProcessing = state === 'processing'

  return (
    <button
      onClick={isRecording ? onStop : isProcessing ? undefined : onStart}
      disabled={isProcessing}
      className={clsx(
        'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200 shadow-sm',
        isRecording
          ? 'bg-red-500 hover:bg-red-600'
          : isProcessing
          ? 'bg-[#1a2744] opacity-50 cursor-not-allowed'
          : 'bg-[#1a2744] hover:bg-[#243560]'
      )}
      aria-label={isRecording ? 'Stop recording' : 'Start recording'}
    >
      {isProcessing ? (
        <Loader2 className="w-5 h-5 text-[#c9a84c] animate-spin" />
      ) : isRecording ? (
        <Square className="w-3.5 h-3.5 text-white fill-white" />
      ) : (
        <Mic className="w-5 h-5 text-[#c9a84c]" />
      )}
    </button>
  )
}
