import { useState } from 'react'
import { Phone, PhoneCall, PhoneOff } from 'lucide-react'
import { initiateOutboundCall } from '../lib/api'

type Status = 'idle' | 'dialing' | 'connected' | 'error'

export function CallPanel({ language }: { language: string }) {
  const [digits, setDigits] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [callSid, setCallSid] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleCall = async () => {
    setError(null)
    setStatus('dialing')
    try {
      const res = await initiateOutboundCall(`+91${digits}`, language)
      setCallSid(res.call_sid)
      setStatus('connected')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Call failed')
      setStatus('error')
    }
  }

  const reset = () => {
    setStatus('idle')
    setCallSid(null)
    setError(null)
  }

  return (
    <div className="flex-1 flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-sm space-y-6">

        {/* Icon */}
        <div className="flex justify-center">
          <div className="w-20 h-20 rounded-full bg-[#1a2744] flex items-center justify-center shadow-lg">
            {status === 'connected'
              ? <PhoneCall className="w-9 h-9 text-[#c9a84c] animate-pulse" />
              : <Phone className="w-9 h-9 text-[#c9a84c]" />}
          </div>
        </div>

        {/* Heading */}
        <div className="text-center">
          <h2 className="font-serif text-2xl text-[#1a2744]">Call a Customer</h2>
          <p className="text-sm text-[#6b7280] mt-1 leading-relaxed">
            Enter an Indian mobile number — the bot will call and<br />speak with them in{' '}
            <span className="text-[#c9a84c] font-medium">
              {language === 'hi-IN' ? 'Hindi' : 'English'}
            </span>.
          </p>
        </div>

        {/* Input + button */}
        {(status === 'idle' || status === 'error') && (
          <div className="space-y-3">
            <div className="flex items-center border border-[#ede5d4] rounded-sm overflow-hidden focus-within:border-[#c9a84c] bg-white transition-colors">
              <span className="px-3 py-3 text-sm text-[#6b7280] border-r border-[#ede5d4] bg-[#f9f5ee] select-none">
                +91
              </span>
              <input
                type="tel"
                value={digits}
                onChange={(e) => setDigits(e.target.value.replace(/\D/g, '').slice(0, 10))}
                placeholder="98XXXXXXXX"
                className="flex-1 px-4 py-3 text-sm text-[#2d2d2d] placeholder-[#9ca3af] outline-none"
              />
            </div>
            {error && <p className="text-xs text-red-500 px-1">{error}</p>}
            <button
              onClick={handleCall}
              disabled={digits.length < 10}
              className="w-full bg-[#1a2744] hover:bg-[#243560] disabled:opacity-40 text-[#c9a84c] py-3 rounded-sm text-sm font-medium flex items-center justify-center gap-2 transition-colors"
            >
              <Phone className="w-4 h-4" />
              Call Now
            </button>
          </div>
        )}

        {/* Dialing state */}
        {status === 'dialing' && (
          <div className="text-center space-y-3">
            <div className="flex justify-center gap-1.5">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-2 h-2 bg-[#c9a84c] rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
            <p className="text-sm text-[#6b7280]">Dialing +91 {digits}…</p>
          </div>
        )}

        {/* Connected state */}
        {status === 'connected' && (
          <div className="space-y-3 text-center">
            <div className="bg-green-50 border border-green-200 rounded-sm px-4 py-4 space-y-1">
              <p className="text-sm font-medium text-green-700">Call initiated successfully</p>
              <p className="text-sm text-green-600">+91 {digits}</p>
              {callSid && (
                <p className="text-xs text-green-500 font-mono mt-1">{callSid.slice(0, 26)}…</p>
              )}
            </div>
            <button
              onClick={reset}
              className="flex items-center justify-center gap-1.5 text-xs text-[#6b7280] hover:text-red-500 transition-colors w-full py-1"
            >
              <PhoneOff className="w-3.5 h-3.5" />
              Make another call
            </button>
          </div>
        )}

      </div>
    </div>
  )
}
