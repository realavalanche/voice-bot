export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  audioUrl?: string
}

export interface Product {
  id: string
  name: string
  price: number
  category: string
  colors: string[]
  sizes: string[]
  description?: string
  image_url?: string | null
  fit?: string
  fabric?: string
  in_stock?: boolean
}

export interface ChatResponse {
  response: string
  intent: string
  sources: string[]
}

export interface VoiceResponse {
  transcript: string
  response_text: string
  audio_base64: string
  language: string
  intent: string
  processing_time_ms?: number
}
