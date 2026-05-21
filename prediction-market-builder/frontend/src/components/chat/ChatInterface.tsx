import { useState, useEffect, useRef } from 'react'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import { chatWs } from '@/lib/websocket'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '0', role: 'system', content: 'Welcome! I can help you discover markets, create strategies, and analyze predictions. Try: "Show me trending markets" or "Create a strategy"', timestamp: new Date().toISOString() },
  ])
  const [isOpen, setIsOpen] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatWs.connect()
    chatWs.on('chat_response', (data) => {
      setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'assistant', content: data.content, timestamp: new Date().toISOString() }])
    })
    return () => chatWs.disconnect()
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSend(content: string) {
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content, timestamp: new Date().toISOString() }])
  }

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-20 right-6 z-50 rounded-full bg-blue-600 p-3 text-white shadow-lg hover:bg-blue-700"
      >
        {isOpen ? 'X' : 'Chat'}
      </button>
      {isOpen && (
        <div className="fixed bottom-24 right-6 z-50 flex h-[500px] w-[400px] flex-col rounded-lg border border-gray-700 bg-gray-900 shadow-xl">
          <div className="flex-1 overflow-y-auto p-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} role={msg.role} content={msg.content} timestamp={msg.timestamp} />
            ))}
            <div ref={endRef} />
          </div>
          <ChatInput onSend={handleSend} />
        </div>
      )}
    </>
  )
}
