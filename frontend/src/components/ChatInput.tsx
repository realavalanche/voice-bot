import { useState, type FormEvent } from 'react'
import { Send } from 'lucide-react'

interface Props {
  onSend: (text: string) => void
  disabled: boolean
  placeholder?: string
  className?: string
}

export function ChatInput({ onSend, disabled, placeholder = 'Ask about products, sizing, returns…', className = '' }: Props) {
  const [value, setValue] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
  }

  return (
    <form onSubmit={submit} className={`flex gap-2 flex-1 ${className}`}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        className="flex-1 bg-white border border-[#ede5d4] rounded-sm px-4 py-2.5 text-sm text-[#2d2d2d] placeholder-[#6b7280] focus:outline-none focus:border-[#c9a84c] disabled:opacity-50 transition-colors"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="bg-[#1a2744] hover:bg-[#243560] disabled:opacity-40 text-[#c9a84c] px-4 py-2.5 rounded-sm transition-colors flex items-center gap-1.5 text-sm font-medium"
      >
        <Send className="w-4 h-4" />
      </button>
    </form>
  )
}
