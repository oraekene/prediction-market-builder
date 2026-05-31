import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import { useResearchWebSocket, ResearchWebSocket } from './useResearchWebSocket'

function createMockWebSocket() {
  const instances: any[] = []
  let nextId = 0

  class MockWebSocket {
    static OPEN = 1
    static CLOSED = 3
    readyState = 1
    onmessage: ((event: any) => void) | null = null
    onclose: ((event: any) => void) | null = null
    close = vi.fn(() => { this.readyState = MockWebSocket.CLOSED })
    send = vi.fn()
    id = nextId++
    constructor(public url: string) {
      instances.push(this)
    }
  }

  vi.stubGlobal('WebSocket', MockWebSocket as any)

  return {
    get instances() { return instances },
  }
}

describe('ResearchWebSocket class', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

  it('connects to research WebSocket URL', () => {
    const mock = createMockWebSocket()
    const rws = new ResearchWebSocket()
    rws.connect('session-1')
    expect(mock.instances.length).toBe(1)
    expect(mock.instances[0].url).toContain('/ws/research/session-1')
  })

  it('disconnects and cleans up', () => {
    const mock = createMockWebSocket()
    const rws = new ResearchWebSocket()
    rws.connect('session-1')
    rws.disconnect()
    const closedWs = mock.instances[0]
    expect(closedWs.close).toHaveBeenCalled()
  })

  it('sends JSON data', () => {
    const mock = createMockWebSocket()
    const rws = new ResearchWebSocket()
    rws.connect('session-1')
    rws.send({ type: 'ping' })
    expect(mock.instances[0].send).toHaveBeenCalledWith(JSON.stringify({ type: 'ping' }))
  })

  it('reconnects on close', () => {
    const mock = createMockWebSocket()
    const rws = new ResearchWebSocket()
    rws.connect('session-1')
    const initialCount = mock.instances.length
    act(() => {
      mock.instances[0].readyState = 3
      mock.instances[0].onclose?.({} as any)
    })
    vi.advanceTimersByTime(3000)
    expect(mock.instances.length).toBe(initialCount + 1)
  })

  it('dispatches to registered listener on message', () => {
    const mock = createMockWebSocket()
    const rws = new ResearchWebSocket()
    const handler = vi.fn()
    rws.on('result', handler)
    rws.connect('session-1')
    act(() => {
      mock.instances[0].onmessage?.({ data: JSON.stringify({ type: 'result', payload: 'done' }) })
    })
    expect(handler).toHaveBeenCalledWith({ type: 'result', payload: 'done' })
  })

  it('skips malformed messages', () => {
    const mock = createMockWebSocket()
    const rws = new ResearchWebSocket()
    const handler = vi.fn()
    rws.on('result', handler)
    rws.connect('session-1')
    act(() => {
      mock.instances[0].onmessage?.({ data: 'not-json' })
    })
    expect(handler).not.toHaveBeenCalled()
  })

  it('does not reconnect if already connected', () => {
    const mock = createMockWebSocket()
    const rws = new ResearchWebSocket()
    rws.connect('session-1')
    // calling connect again while ws.readyState === 1 should not create new instance
    const countBefore = mock.instances.length
    rws.connect('session-1')
    expect(mock.instances.length).toBe(countBefore)
  })
})

describe('useResearchWebSocket hook', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

  it('returns a send function', () => {
    createMockWebSocket()
    const { result } = renderHook(() => useResearchWebSocket('session-1', {}))
    expect(typeof result.current.send).toBe('function')
  })

  it('connects when sessionId is provided', () => {
    const mock = createMockWebSocket()
    renderHook(() => useResearchWebSocket('session-1', {}))
    expect(mock.instances.length).toBe(1)
  })

  it('does not connect when sessionId is null', () => {
    const mock = createMockWebSocket()
    renderHook(() => useResearchWebSocket(null, {}))
    expect(mock.instances.length).toBe(0)
  })

  it('registers handlers from the handlers object', () => {
    const mock = createMockWebSocket()
    const handlers = { result: vi.fn() }
    renderHook(() => useResearchWebSocket('session-1', handlers))
    act(() => {
      mock.instances[0].onmessage?.({ data: JSON.stringify({ type: 'result', payload: 'hello' }) })
    })
    expect(handlers.result).toHaveBeenCalledWith({ type: 'result', payload: 'hello' })
  })

  it('disconnects on unmount', () => {
    const mock = createMockWebSocket()
    const { unmount } = renderHook(() => useResearchWebSocket('session-1', {}))
    const closeSpy = mock.instances[0].close
    unmount()
    expect(closeSpy).toHaveBeenCalled()
  })

  it('disconnects old session and connects new one when sessionId changes', () => {
    const mock = createMockWebSocket()
    const { rerender } = renderHook(
      ({ sid }: { sid: string | null }) => useResearchWebSocket(sid, {}),
      { initialProps: { sid: 'session-1' } },
    )
    const firstWs = mock.instances[0]
    rerender({ sid: 'session-2' })
    expect(firstWs.close).toHaveBeenCalled()
    expect(mock.instances.length).toBe(2)
  })

  it('sends data via the returned send function', () => {
    const mock = createMockWebSocket()
    const { result } = renderHook(() => useResearchWebSocket('session-1', {}))
    result.current.send({ action: 'stop' })
    expect(mock.instances[0].send).toHaveBeenCalledWith(JSON.stringify({ action: 'stop' }))
  })
})
