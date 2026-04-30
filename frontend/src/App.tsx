import { useState, useEffect, useRef } from 'react'
import { Trash2, Square } from 'lucide-react'
import { Header } from './components/Header'
import { MicButton } from './components/MicButton'
import { ChatMessage } from './components/ChatMessage'
import { ChatInput } from './components/ChatInput'
import { ErrorBanner } from './components/ErrorBanner'
import { CallPanel } from './components/CallPanel'
import { useVoiceRecorder } from './hooks/useVoiceRecorder'
import { useChat } from './hooks/useChat'
import './index.css'

export default function App() {
  const [language, setLanguage] = useState('en-IN')
  const [tab, setTab] = useState<'chat' | 'call'>('chat')
  const [chatError, setChatError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const { state: recState, error: micError, start, stop } = useVoiceRecorder()
  const { messages, loading, error: apiError, sendText, sendVoice, clear } = useChat(language)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (apiError) setChatError(apiError)
    else if (micError) setChatError(micError)
  }, [apiError, micError])

  return (
    <div className="min-h-screen bg-[#f5f0e8] flex flex-col">
      <Header language={language} onLanguageChange={setLanguage} />

      <main className="flex-1 flex flex-col max-w-3xl mx-auto w-full">
        {/* Tab bar */}
        <div className="flex border-b border-[#ede5d4] bg-white">
          {(['chat', 'call'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                tab === t
                  ? 'text-[#1a2744] border-b-2 border-[#c9a84c]'
                  : 'text-[#6b7280] hover:text-[#1a2744]'
              }`}
            >
              {t === 'chat' ? 'Chat / Voice' : 'Call Customer'}
            </button>
          ))}
        </div>

        {tab === 'call' ? (
          <CallPanel language={language} />
        ) : (
          <>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[400px]">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-16 text-center">
              <div className="text-[#c9a84c] text-5xl font-serif mb-4">R&amp;T</div>
              <p className="text-[#6b7280] text-sm max-w-xs leading-relaxed">
                {language === 'hi-IN'
                  ? 'बोलें या टाइप करें — products, sizing, या returns के बारे में पूछें'
                  : 'Speak or type to ask about products, sizing, or returns'}
              </p>
            </div>
          ) : (
            messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
          )}
          {loading && (
            <div className="flex gap-2 items-center text-[#6b7280] text-sm">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-1.5 h-1.5 bg-[#c9a84c] rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
              Thinking…
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {chatError && (
          <div className="px-4 pb-2">
            <ErrorBanner message={chatError} onDismiss={() => setChatError(null)} />
          </div>
        )}

        {/* Input area */}
        <div className="border-t border-[#ede5d4] bg-white px-4 pb-4 pt-3">
          {recState === 'recording' ? (
            /* Recording — full-width inline bar */
            <div className="flex items-center gap-3 rounded-sm bg-red-50 border border-red-200 px-4 py-2.5">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse flex-shrink-0" />
              <span className="flex-1 text-sm text-red-600">Listening… auto-stops on silence</span>
              <div className="flex items-end gap-0.5 h-4 mx-1">
                {[0, 1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="waveform-bar w-1 bg-red-400 rounded-full"
                    style={{ animationDelay: `${i * 0.12}s` }}
                  />
                ))}
              </div>
              <button
                onClick={stop}
                className="flex-shrink-0 w-8 h-8 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center transition-colors"
                aria-label="Stop recording"
              >
                <Square className="w-3.5 h-3.5 text-white fill-white" />
              </button>
            </div>
          ) : (
            /* Idle / processing — unified mic + text row */
            <div className="flex items-center gap-2">
              <MicButton
                state={recState}
                onStart={() => start(sendVoice)}
                onStop={stop}
              />
              <ChatInput onSend={sendText} disabled={loading || recState !== 'idle'} />
            </div>
          )}

          {/* Status row */}
          <div className="flex items-center justify-between mt-2 px-0.5">
            <span className="flex items-center gap-1.5 text-xs text-[#6b7280]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#c9a84c] inline-block" />
              {language === 'hi-IN' ? 'हिन्दी में जवाब देगा' : 'Responding in English'}
            </span>
            {messages.length > 0 && (
              <button
                onClick={clear}
                className="flex items-center gap-1 text-xs text-[#6b7280] hover:text-red-500 transition-colors"
              >
                <Trash2 className="w-3 h-3" />
                Clear
              </button>
            )}
          </div>
        </div>
          </>
        )}
      </main>
    </div>
  )
}
