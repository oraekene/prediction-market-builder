import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import {
  usePaperWallet, useResetWallet, usePlacePaperOrder, usePaperOrders,
  useCancelPaperOrder, usePaperPerformance, useSyncResolutions,
  usePaperMetric, useCompareStrategies,
} from './usePaperTrading'

const mockFetchPaperWallet = vi.fn()
const mockResetPaperWallet = vi.fn()
const mockPlacePaperOrder = vi.fn()
const mockFetchPaperOrders = vi.fn()
const mockCancelPaperOrder = vi.fn()
const mockFetchPaperPerformance = vi.fn()
const mockComparePaperStrategies = vi.fn()
const mockSyncPaperResolutions = vi.fn()
const mockFetchPaperMetric = vi.fn()

vi.mock('@/lib/api_paper', () => ({
  fetchPaperWallet: (...args: any[]) => mockFetchPaperWallet(...args),
  resetPaperWallet: (...args: any[]) => mockResetPaperWallet(...args),
  placePaperOrder: (...args: any[]) => mockPlacePaperOrder(...args),
  fetchPaperOrders: (...args: any[]) => mockFetchPaperOrders(...args),
  cancelPaperOrder: (...args: any[]) => mockCancelPaperOrder(...args),
  fetchPaperPerformance: (...args: any[]) => mockFetchPaperPerformance(...args),
  comparePaperStrategies: (...args: any[]) => mockComparePaperStrategies(...args),
  syncPaperResolutions: (...args: any[]) => mockSyncPaperResolutions(...args),
  fetchPaperMetric: (...args: any[]) => mockFetchPaperMetric(...args),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('usePaperWallet', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns wallet data', async () => {
    const wallet = { id: 'wallet-1', cash_balance: 10000, total_value: 12500, market_value: 2500, pnl: 2500, pnl_percent: 0.25, position_count: 3 }
    mockFetchPaperWallet.mockResolvedValue(wallet)
    const { result } = renderHook(() => usePaperWallet(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(wallet)
    expect(mockFetchPaperWallet).toHaveBeenCalledWith('default')
  })

  it('passes custom userId', async () => {
    mockFetchPaperWallet.mockResolvedValue({})
    renderHook(() => usePaperWallet('user-42'), { wrapper: createWrapper() })
    await waitFor(() => expect(mockFetchPaperWallet).toHaveBeenCalledWith('user-42'))
  })
})

describe('useResetWallet', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls resetPaperWallet on mutation', async () => {
    mockResetPaperWallet.mockResolvedValue({ cash_balance: 10000 })
    const { result } = renderHook(() => useResetWallet(), { wrapper: createWrapper() })
    result.current.mutate('user-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockResetPaperWallet).toHaveBeenCalledWith('user-1')
  })
})

describe('usePlacePaperOrder', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls placePaperOrder on mutation', async () => {
    const order = { market_id: 'm-1', side: 'buy', amount: 100 }
    mockPlacePaperOrder.mockResolvedValue(order)
    const { result } = renderHook(() => usePlacePaperOrder(), { wrapper: createWrapper() })
    result.current.mutate(order)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockPlacePaperOrder).toHaveBeenCalledWith(order, expect.any(Object))
  })
})

describe('usePaperOrders', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns orders list', async () => {
    mockFetchPaperOrders.mockResolvedValue([])
    const { result } = renderHook(() => usePaperOrders('wallet-1', 'filled'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockFetchPaperOrders).toHaveBeenCalledWith('wallet-1', 'filled')
  })
})

describe('useCancelPaperOrder', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls cancelPaperOrder on mutation', async () => {
    mockCancelPaperOrder.mockResolvedValue(undefined)
    const { result } = renderHook(() => useCancelPaperOrder(), { wrapper: createWrapper() })
    result.current.mutate('order-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockCancelPaperOrder).toHaveBeenCalledWith('order-1', expect.any(Object))
  })
})

describe('usePaperPerformance', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns performance data', async () => {
    const perf = { total_trades: 25, win_rate: 0.6, sharpe: 1.8 }
    mockFetchPaperPerformance.mockResolvedValue(perf)
    const { result } = renderHook(() => usePaperPerformance('strat-1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(perf)
  })
})

describe('useSyncResolutions', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls syncPaperResolutions on mutation', async () => {
    mockSyncPaperResolutions.mockResolvedValue(undefined)
    const { result } = renderHook(() => useSyncResolutions(), { wrapper: createWrapper() })
    result.current.mutate(['order-1', 'order-2'])
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockSyncPaperResolutions).toHaveBeenCalledWith(['order-1', 'order-2'], expect.any(Object))
  })
})

describe('usePaperMetric', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('is disabled by default', () => {
    const { result } = renderHook(() => usePaperMetric('sharpe'), { wrapper: createWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useCompareStrategies', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('is disabled with fewer than 2 IDs', () => {
    const { result } = renderHook(() => useCompareStrategies(['strat-1']), { wrapper: createWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })

  it('fetches when 2+ IDs provided', async () => {
    mockComparePaperStrategies.mockResolvedValue([])
    const { result } = renderHook(() => useCompareStrategies(['strat-1', 'strat-2']), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockComparePaperStrategies).toHaveBeenCalledWith(['strat-1', 'strat-2'])
  })
})
