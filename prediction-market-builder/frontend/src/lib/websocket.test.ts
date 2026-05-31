import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ChatWebSocket } from './websocket'

function createMockWebSocket() {
  let onmessage: ((event: MessageEvent) => void) | null = null
  let onclose: ((event: CloseEvent) => void) | null = null
  let constructorCallCount = 0

  const send = vi.fn()
  const close = vi.fn()

  class MockWebSocket {
    static OPEN = 1
    readyState = 1
    send = send
    close = close
    constructor(...args: any[]) {
      constructorCallCount++
    }
    set onmessage(fn: any) { onmessage = fn }
    get onmessage() { return onmessage }
    set onclose(fn: any) { onclose = fn }
    get onclose() { return onclose }
  }

  vi.stubGlobal('WebSocket', MockWebSocket as any)

  return {
    get constructorCallCount() { return constructorCallCount },
    send,
    close,
    triggerMessage: (data: string) => onmessage?.({ data } as MessageEvent),
    triggerClose: () => onclose?.({} as CloseEvent),
  }
}

describe('ChatWebSocket', () => {
  let ws: ChatWebSocket
  let mock: ReturnType<typeof createMockWebSocket>

  beforeEach(() => {
    vi.useFakeTimers()
    mock = createMockWebSocket()
    ws = new ChatWebSocket()
  })

  afterEach(() => {
    ws.disconnect()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('connects and creates WebSocket', () => {
    ws.connect()
    expect(mock.constructorCallCount).toBe(1)
  })

  it('sends JSON message when connected', () => {
    ws.connect()
    ws.send('chat_message', { content: 'hello' })
    expect(mock.send).toHaveBeenCalledWith(JSON.stringify({ type: 'chat_message', payload: { content: 'hello' } }))
  })

  it('registers event listeners via on()', () => {
    const handler = vi.fn()
    ws.on('message', handler)
    ws.connect()
    mock.triggerMessage(JSON.stringify({ type: 'message', payload: 'hi' }))
    expect(handler).toHaveBeenCalledWith({ type: 'message', payload: 'hi' })
  })

  it('reconnects on close', () => {
    ws.connect()
    const beforeCount = mock.constructorCallCount
    mock.triggerClose()
    vi.advanceTimersByTime(3000)
    expect(mock.constructorCallCount).toBe(beforeCount + 1)
  })

  it('does not reconnect after disconnect()', () => {
    ws.connect()
    ws.disconnect()
    const beforeCount = mock.constructorCallCount
    mock.triggerClose()
    vi.advanceTimersByTime(3000)
    expect(mock.constructorCallCount).toBe(beforeCount)
  })

  it('disconnect cleans up', () => {
    ws.connect()
    ws.disconnect()
    expect(mock.close).toHaveBeenCalled()
  })
})
