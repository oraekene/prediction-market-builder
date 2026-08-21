import { getToken } from '@/lib/auth'

function wsUrl(path: string): string {
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const token = getToken()
  const separator = path.includes('?') ? '&' : '?'
  return `${scheme}://${window.location.host}${path}${separator}token=${encodeURIComponent(token || '')}`
}

export class ChatWebSocket {
  private ws: WebSocket | null = null
  private listeners: Map<string, (data: any) => void> = new Map()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private shouldReconnect = false

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }
    this.shouldReconnect = true
    this.ws = new WebSocket(wsUrl('/ws/chat'))

    this.ws.onmessage = (event) => {
      let msg: any
      try {
        msg = JSON.parse(event.data)
      } catch {
        return
      }
      const handler = this.listeners.get(msg.type)
      if (handler) handler(msg)
    }

    this.ws.onclose = () => {
      this.ws = null
      if (this.shouldReconnect) {
        this.reconnectTimer = setTimeout(() => this.connect(), 3000)
      }
    }
  }

  send(type: string, payload: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }))
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

export const chatWs = new ChatWebSocket()
