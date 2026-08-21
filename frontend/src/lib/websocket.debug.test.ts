import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ChatWebSocket } from './websocket'

describe('debug4', () => {
  it('inspect ws state', async () => {
    const { getToken } = await import('@/lib/auth')
    console.log('token:', JSON.stringify(getToken()))
    let capturedUrl = ''
    let n = 0
    class MockWebSocket {
      static OPEN = 1
      static CONNECTING = 0
      readyState = 1
      send = vi.fn()
      close = vi.fn()
      constructor(url: string) { n++; capturedUrl = url }
    }
    vi.stubGlobal('WebSocket', MockWebSocket as any)
    vi.useFakeTimers()
    const ws = new ChatWebSocket()
    ws.connect()
    console.log('count:', n, 'url:', capturedUrl)
    vi.useRealTimers()
    expect(n).toBe(1)
  })
})
