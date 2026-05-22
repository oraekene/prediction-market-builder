import { useEffect, useRef } from 'react'

export function useWebSocket(url: string, onMessage: (data: any) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)
  const disconnectedRef = useRef(false)

  onMessageRef.current = onMessage

  useEffect(() => {
    disconnectedRef.current = false
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    function connect() {
      if (disconnectedRef.current) return
      const ws = new WebSocket(url)
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessageRef.current(data)
        } catch {
          /* skip malformed messages */
        }
      }
      ws.onclose = () => {
        if (!disconnectedRef.current) {
          reconnectTimer = setTimeout(connect, 3000)
        }
      }
      wsRef.current = ws
    }

    connect()

    return () => {
      disconnectedRef.current = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [url])

  return wsRef
}
