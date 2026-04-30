import type { ChatResponse, VoiceResponse, Product } from '../types'

const BASE = import.meta.env.VITE_API_URL ?? ''

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function sendTextMessage(
  message: string,
  language: string,
  history: { role: string; content: string }[]
): Promise<ChatResponse> {
  return post('/api/chat', { message, language, history })
}

export async function sendVoiceMessage(
  audioBlob: Blob,
  language: string
): Promise<VoiceResponse> {
  const form = new FormData()
  form.append('audio', audioBlob, 'recording.wav')
  form.append('language', language)
  const res = await fetch(`${BASE}/api/voice-chat`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export async function fetchProducts(query?: string): Promise<Product[]> {
  const url = query
    ? `${BASE}/api/products?q=${encodeURIComponent(query)}`
    : `${BASE}/api/products`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  const data = await res.json()
  return data.products ?? data
}

export async function initiateOutboundCall(
  phoneNumber: string,
  language: string
): Promise<{ call_sid: string; status: string }> {
  return post('/api/calls/outbound', { phone_number: phoneNumber, language })
}
