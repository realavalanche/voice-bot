import { useState, useCallback } from 'react'
import { sendTextMessage, sendVoiceMessage } from '../lib/api'
import type { Message } from '../types'

function uid() {
  return Math.random().toString(36).slice(2)
}

export function useChat(language: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addMsg = (msg: Message) =>
    setMessages((prev) => [...prev, msg])

  const sendText = useCallback(
    async (text: string) => {
      const userMsg: Message = {
        id: uid(), role: 'user', content: text, timestamp: new Date(),
      }
      addMsg(userMsg)
      setLoading(true)
      setError(null)
      try {
        const history = messages.map((m) => ({ role: m.role, content: m.content }))
        const res = await sendTextMessage(text, language, history)
        addMsg({ id: uid(), role: 'assistant', content: res.response, timestamp: new Date() })
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Request failed')
      } finally {
        setLoading(false)
      }
    },
    [messages, language]
  )

  const sendVoice = useCallback(
    async (blob: Blob) => {
      setLoading(true)
      setError(null)
      try {
        const res = await sendVoiceMessage(blob, language)
        addMsg({ id: uid(), role: 'user', content: res.transcript, timestamp: new Date() })
        const audioUrl = res.audio_base64
          ? `data:audio/wav;base64,${res.audio_base64}`
          : undefined
        addMsg({
          id: uid(), role: 'assistant', content: res.response_text,
          timestamp: new Date(), audioUrl,
        })
        if (audioUrl) {
          new Audio(audioUrl).play().catch(() => {})
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Voice request failed')
      } finally {
        setLoading(false)
      }
    },
    [language]
  )

  const clear = useCallback(() => setMessages([]), [])

  return { messages, loading, error, sendText, sendVoice, clear }
}
