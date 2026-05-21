export class ChatWebSocket {
  private ws: WebSocket | null = null
  private listeners: Map<string, (data: any) => void> = new Map()

  connect() {
    this.ws = new WebSocket(`ws://${window.location.host}/ws/chat`)
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      const handler = this.listeners.get(msg.type)
      if (handler) handler(msg)
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
    this.ws?.close()
  }
}

export const chatWs = new ChatWebSocket()
