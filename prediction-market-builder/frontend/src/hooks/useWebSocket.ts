import { useEffect, useRef, useCallback } from 'react'

export function useWebSocket(url: string, onMessage: (data: any) => void) {
  const wsRef = useRef<WebSocket | null>(null)

  const connect = useCallback(() => {
    const ws = new WebSocket(url)
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      onMessage(data)
    }
    ws.onclose = () => {
      setTimeout(connect, 3000)
    }
    wsRef.current = ws
  }, [url, onMessage])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  return wsRef
}
