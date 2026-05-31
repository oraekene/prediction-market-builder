import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import { useWebSocket } from './useWebSocket'

function createMockWebSocket() {
  let connected = false
  const instances: any[] = []

  class MockWebSocket {
    static OPEN = 1
    readyState = 1
    onmessage: ((event: any) => void) | null = null
    onclose: ((event: any) => void) | null = null
    close = vi.fn(() => { connected = false })
    constructor(public url: string) {
      connected = true
      instances.push(this)
    }
  }

  vi.stubGlobal('WebSocket', MockWebSocket as any)

  return {
    get connected() { return connected },
    get instances() { return instances },
  }
}

describe('useWebSocket', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

  it('connects to the given URL', () => {
    const mock = createMockWebSocket()
    const onMessage = vi.fn()
    renderHook(() => useWebSocket('ws://example.com/ws', onMessage))
    expect(mock.instances.length).toBe(1)
    expect(mock.instances[0].url).toBe('ws://example.com/ws')
  })

  it('calls onMessage when a JSON message is received', () => {
    const mock = createMockWebSocket()
    const onMessage = vi.fn()
    renderHook(() => useWebSocket('ws://example.com/ws', onMessage))
    act(() => {
      mock.instances[0].onmessage?.({ data: JSON.stringify({ type: 'update', payload: 'test' }) })
    })
    expect(onMessage).toHaveBeenCalledWith({ type: 'update', payload: 'test' })
  })

  it('does not call onMessage for malformed JSON', () => {
    const mock = createMockWebSocket()
    const onMessage = vi.fn()
    renderHook(() => useWebSocket('ws://example.com/ws', onMessage))
    act(() => {
      mock.instances[0].onmessage?.({ data: 'not-json' })
    })
    expect(onMessage).not.toHaveBeenCalled()
  })

  it('reconnects on close', () => {
    const mock = createMockWebSocket()
    const onMessage = vi.fn()
    renderHook(() => useWebSocket('ws://example.com/ws', onMessage))
    const initialCount = mock.instances.length
    act(() => {
      mock.instances[0].onclose?.({} as any)
    })
    vi.advanceTimersByTime(3000)
    expect(mock.instances.length).toBe(initialCount + 1)
  })

  it('disconnects on unmount', () => {
    const mock = createMockWebSocket()
    const onMessage = vi.fn()
    const { unmount } = renderHook(() => useWebSocket('ws://example.com/ws', onMessage))
    const closeSpy = mock.instances[0].close
    unmount()
    expect(closeSpy).toHaveBeenCalled()
  })
})
