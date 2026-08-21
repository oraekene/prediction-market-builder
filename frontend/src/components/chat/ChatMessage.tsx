import { cn } from '@/lib/utils'

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export default function ChatMessage({ role, content, timestamp }: ChatMessageProps) {
  return (
    <div className={cn('mb-3 flex', role === 'user' ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          role === 'user' && 'bg-blue-600 text-white',
          role === 'assistant' && 'bg-gray-800 text-gray-100',
          role === 'system' && 'bg-gray-950 text-gray-400 text-xs italic',
        )}
      >
        <p className="text-sm">{content}</p>
        {timestamp && <p className="mt-1 text-right text-xs opacity-50">{timestamp}</p>}
      </div>
    </div>
  )
}
