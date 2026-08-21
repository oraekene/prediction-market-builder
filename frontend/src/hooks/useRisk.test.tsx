import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useRiskSummary, useVaR, useCorrelation, useDrawdown, usePortfolioRisk } from './useRisk'

const mockFetchRiskSummary = vi.fn()
const mockFetchVaR = vi.fn()
const mockFetchCorrelation = vi.fn()
const mockFetchDrawdown = vi.fn()
const mockFetchPortfolioRisk = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchRiskSummary: (...args: any[]) => mockFetchRiskSummary(...args),
  fetchVaR: (...args: any[]) => mockFetchVaR(...args),
  fetchCorrelation: (...args: any[]) => mockFetchCorrelation(...args),
  fetchDrawdown: (...args: any[]) => mockFetchDrawdown(...args),
  fetchPortfolioRisk: (...args: any[]) => mockFetchPortfolioRisk(...args),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('useRiskSummary', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns risk summary', async () => {
    const data = { current_drawdown: 0.05, max_drawdown: 0.15, var_95: 0.02, var_99: 0.04, correlation_count: 10, position_count: 5 }
    mockFetchRiskSummary.mockResolvedValue(data)
    const { result } = renderHook(() => useRiskSummary(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })
})

describe('useVaR', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns VaR with default confidence', async () => {
    mockFetchVaR.mockResolvedValue(0.02)
    const { result } = renderHook(() => useVaR(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockFetchVaR).toHaveBeenCalledWith(0.95)
  })

  it('passes custom confidence', async () => {
    mockFetchVaR.mockResolvedValue(0.04)
    const { result } = renderHook(() => useVaR(0.99), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockFetchVaR).toHaveBeenCalledWith(0.99)
  })
})

describe('useCorrelation', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns correlation data', async () => {
    const data = [{ id1: 'm-1', id2: 'm-2', correlation: 0.65 }]
    mockFetchCorrelation.mockResolvedValue(data)
    const { result } = renderHook(() => useCorrelation(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })
})

describe('useDrawdown', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns drawdown data', async () => {
    const data = { current_drawdown: 0.05, max_drawdown: 0.15 }
    mockFetchDrawdown.mockResolvedValue(data)
    const { result } = renderHook(() => useDrawdown(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })
})

describe('usePortfolioRisk', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns portfolio risk data', async () => {
    const data = { var: 0.02, expected_shortfall: 0.03 }
    mockFetchPortfolioRisk.mockResolvedValue(data)
    const { result } = renderHook(() => usePortfolioRisk(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })
})
