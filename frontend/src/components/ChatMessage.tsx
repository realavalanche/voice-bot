import { Volume2 } from 'lucide-react'
import clsx from 'clsx'
import type { Message } from '../types'

interface Props {
  message: Message
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'

  const playAudio = () => {
    if (message.audioUrl) new Audio(message.audioUrl).play().catch(() => {})
  }

  return (
    <div className={clsx('flex gap-3 max-w-2xl', isUser ? 'ml-auto flex-row-reverse' : '')}>
      <div
        className={clsx(
          'w-8 h-8 rounded-sm flex-shrink-0 flex items-center justify-center text-xs font-semibold',
          isUser ? 'bg-[#c9a84c] text-[#1a2744]' : 'bg-[#1a2744] text-[#c9a84c]'
        )}
      >
        {isUser ? 'U' : 'R'}
      </div>
      <div
        className={clsx(
          'rounded-sm px-4 py-3 text-sm leading-relaxed max-w-sm',
          isUser
            ? 'bg-[#1a2744] text-[#f5f0e8]'
            : 'bg-white text-[#2d2d2d] shadow-sm border border-[#ede5d4]'
        )}
      >
        <p>{message.content}</p>
        {message.audioUrl && !isUser && (
          <button
            onClick={playAudio}
            className="mt-2 flex items-center gap-1 text-[#c9a84c] text-xs hover:text-[#a8862f] transition-colors"
          >
            <Volume2 className="w-3 h-3" />
            Play audio
          </button>
        )}
        <time className="block mt-1 text-xs opacity-40">
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </time>
      </div>
    </div>
  )
}
