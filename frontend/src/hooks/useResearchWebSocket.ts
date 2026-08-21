import { useEffect, useRef, useCallback } from 'react'
import { getToken } from '@/lib/auth'

function wsUrl(path: string): string {
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const token = getToken()
  const separator = path.includes('?') ? '&' : '?'
  return `${scheme}://${window.location.host}${path}${separator}token=${encodeURIComponent(token || '')}`
}

export class ResearchWebSocket {
  private ws: WebSocket | null = null
  private listeners: Map<string, (data: any) => void> = new Map()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private shouldReconnect = false

  connect(sessionId: string) {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }
    this.shouldReconnect = true
    this.ws = new WebSocket(wsUrl(`/api/research/ws/research/${sessionId}`))
    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        const handler = this.listeners.get(msg.type)
        if (handler) handler(msg)
      } catch { /* skip malformed */ }
    }
    this.ws.onclose = () => {
      this.ws = null
      if (this.shouldReconnect) {
        this.reconnectTimer = setTimeout(() => this.connect(sessionId), 3000)
      }
    }
  }

  send(data: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  on(type: string, handler: (data: any) => void) {
    this.listeners.set(type, handler)
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }
}

export function useResearchWebSocket(
  sessionId: string | null,
  handlers: Record<string, (data: any) => void>,
) {
  const wsRef = useRef<ResearchWebSocket | null>(null)
  const handlersRef = useRef(handlers)
  handlersRef.current = handlers

  useEffect(() => {
    if (!sessionId) return
    const ws = new ResearchWebSocket()
    wsRef.current = ws
    for (const [type, handler] of Object.entries(handlersRef.current)) {
      ws.on(type, handler)
    }
    ws.connect(sessionId)
    return () => ws.disconnect()
  }, [sessionId])

  const send = useCallback((data: Record<string, unknown>) => {
    wsRef.current?.send(data)
  }, [])

  return { send }
}
