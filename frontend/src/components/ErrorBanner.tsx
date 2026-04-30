import { X, AlertCircle } from 'lucide-react'

interface Props {
  message: string
  onDismiss: () => void
}

export function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2.5 rounded-sm">
      <AlertCircle className="w-4 h-4 flex-shrink-0" />
      <span className="flex-1">{message}</span>
      <button onClick={onDismiss} className="hover:text-red-900 transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
