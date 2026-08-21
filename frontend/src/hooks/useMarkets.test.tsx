import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useMarkets, useMarket } from './useMarkets'
import { createMockMarket, createMockMarkets } from '@/test/mocks'

const mockFetchMarkets = vi.fn()
const mockFetchMarket = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchMarkets: (...args: any[]) => mockFetchMarkets(...args),
  fetchMarket: (...args: any[]) => mockFetchMarket(...args),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('useMarkets', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns markets data on success', async () => {
    const markets = createMockMarkets(3)
    mockFetchMarkets.mockResolvedValue(markets)
    const { result } = renderHook(() => useMarkets(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(markets)
    expect(mockFetchMarkets).toHaveBeenCalledWith(undefined)
  })

  it('passes params to fetchMarkets', async () => {
    mockFetchMarkets.mockResolvedValue([])
    const params = { platform: 'polymarket', status: 'active' }
    renderHook(() => useMarkets(params), { wrapper: createWrapper() })
    await waitFor(() => expect(mockFetchMarkets).toHaveBeenCalledWith(params))
  })
})

describe('useMarket', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns market data on success', async () => {
    const market = createMockMarket()
    mockFetchMarket.mockResolvedValue(market)
    const { result } = renderHook(() => useMarket('market-1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(market)
    expect(mockFetchMarket).toHaveBeenCalledWith('market-1')
  })

  it('is not enabled when id is empty', async () => {
    const { result } = renderHook(() => useMarket(''), { wrapper: createWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })
})
