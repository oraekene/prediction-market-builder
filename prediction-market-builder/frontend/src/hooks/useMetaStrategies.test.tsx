import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import {
  useMetaStrategies, useMetaStrategy, useCreateMetaStrategy,
  useUpdateMetaStrategy, useDeleteMetaStrategy, useAddStrategyToMetaPool,
  useRemoveStrategyFromMetaPool, useMetaRankings, useEvaluateMetaPromotion,
  useMetaPerformance, useForceMetaPromote,
} from './useMetaStrategies'

const mockFetchMetaStrategies = vi.fn()
const mockCreateMetaStrategy = vi.fn()
const mockFetchMetaStrategy = vi.fn()
const mockUpdateMetaStrategy = vi.fn()
const mockDeleteMetaStrategy = vi.fn()
const mockAddStrategyToMetaPool = vi.fn()
const mockRemoveStrategyFromMetaPool = vi.fn()
const mockFetchMetaRankings = vi.fn()
const mockEvaluateMetaPromotion = vi.fn()
const mockForceMetaPromote = vi.fn()
const mockFetchMetaPerformance = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchMetaStrategies: (...args: any[]) => mockFetchMetaStrategies(...args),
  createMetaStrategy: (...args: any[]) => mockCreateMetaStrategy(...args),
  fetchMetaStrategy: (...args: any[]) => mockFetchMetaStrategy(...args),
  updateMetaStrategy: (...args: any[]) => mockUpdateMetaStrategy(...args),
  deleteMetaStrategy: (...args: any[]) => mockDeleteMetaStrategy(...args),
  addStrategyToMetaPool: (...args: any[]) => mockAddStrategyToMetaPool(...args),
  removeStrategyFromMetaPool: (...args: any[]) => mockRemoveStrategyFromMetaPool(...args),
  fetchMetaRankings: (...args: any[]) => mockFetchMetaRankings(...args),
  evaluateMetaPromotion: (...args: any[]) => mockEvaluateMetaPromotion(...args),
  forceMetaPromote: (...args: any[]) => mockForceMetaPromote(...args),
  fetchMetaPerformance: (...args: any[]) => mockFetchMetaPerformance(...args),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('useMetaStrategies', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns meta-strategies list', async () => {
    const data = [{ id: 'meta-1', name: 'Test', mode: 'rankings', status: 'active', pool_size: 5, winner: null }]
    mockFetchMetaStrategies.mockResolvedValue(data)
    const { result } = renderHook(() => useMetaStrategies(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })
})

describe('useMetaStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns a single meta-strategy', async () => {
    const data = { id: 'meta-1', name: 'Test', mode: 'rankings', status: 'active', pool_size: 5, winner: null }
    mockFetchMetaStrategy.mockResolvedValue(data)
    const { result } = renderHook(() => useMetaStrategy('meta-1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('is disabled when id is empty', () => {
    const { result } = renderHook(() => useMetaStrategy(''), { wrapper: createWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useCreateMetaStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls createMetaStrategy on mutation', async () => {
    mockCreateMetaStrategy.mockResolvedValue({ id: 'meta-2' })
    const { result } = renderHook(() => useCreateMetaStrategy(), { wrapper: createWrapper() })
    result.current.mutate({ name: 'New', mode: 'rankings' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockCreateMetaStrategy).toHaveBeenCalledWith({ name: 'New', mode: 'rankings' }, expect.any(Object))
  })
})

describe('useUpdateMetaStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls updateMetaStrategy on mutation', async () => {
    mockUpdateMetaStrategy.mockResolvedValue(undefined)
    const { result } = renderHook(() => useUpdateMetaStrategy(), { wrapper: createWrapper() })
    result.current.mutate({ id: 'meta-1', data: { name: 'Updated' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockUpdateMetaStrategy).toHaveBeenCalledWith('meta-1', { name: 'Updated' })
  })
})

describe('useDeleteMetaStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls deleteMetaStrategy on mutation', async () => {
    mockDeleteMetaStrategy.mockResolvedValue(undefined)
    const { result } = renderHook(() => useDeleteMetaStrategy(), { wrapper: createWrapper() })
    result.current.mutate('meta-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockDeleteMetaStrategy).toHaveBeenCalledWith('meta-1', expect.any(Object))
  })
})

describe('useAddStrategyToMetaPool', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls addStrategyToMetaPool on mutation', async () => {
    mockAddStrategyToMetaPool.mockResolvedValue(undefined)
    const { result } = renderHook(() => useAddStrategyToMetaPool(), { wrapper: createWrapper() })
    result.current.mutate({ msId: 'meta-1', strategyId: 'strat-1' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockAddStrategyToMetaPool).toHaveBeenCalledWith('meta-1', 'strat-1')
  })
})

describe('useRemoveStrategyFromMetaPool', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls removeStrategyFromMetaPool on mutation', async () => {
    mockRemoveStrategyFromMetaPool.mockResolvedValue(undefined)
    const { result } = renderHook(() => useRemoveStrategyFromMetaPool(), { wrapper: createWrapper() })
    result.current.mutate({ msId: 'meta-1', strategyId: 'strat-1' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockRemoveStrategyFromMetaPool).toHaveBeenCalledWith('meta-1', 'strat-1')
  })
})

describe('useMetaRankings', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns rankings', async () => {
    mockFetchMetaRankings.mockResolvedValue([])
    const { result } = renderHook(() => useMetaRankings('meta-1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockFetchMetaRankings).toHaveBeenCalledWith('meta-1')
  })

  it('is disabled when id is empty', () => {
    const { result } = renderHook(() => useMetaRankings(''), { wrapper: createWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useEvaluateMetaPromotion', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls evaluateMetaPromotion on mutation', async () => {
    mockEvaluateMetaPromotion.mockResolvedValue(undefined)
    const { result } = renderHook(() => useEvaluateMetaPromotion(), { wrapper: createWrapper() })
    result.current.mutate('meta-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockEvaluateMetaPromotion).toHaveBeenCalledWith('meta-1', expect.any(Object))
  })
})

describe('useMetaPerformance', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns performance data', async () => {
    const data = { sharpe: 1.5, win_rate: 0.6 }
    mockFetchMetaPerformance.mockResolvedValue(data)
    const { result } = renderHook(() => useMetaPerformance('meta-1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })

  it('is disabled when id is empty', () => {
    const { result } = renderHook(() => useMetaPerformance(''), { wrapper: createWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useForceMetaPromote', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls forceMetaPromote on mutation', async () => {
    mockForceMetaPromote.mockResolvedValue(undefined)
    const { result } = renderHook(() => useForceMetaPromote(), { wrapper: createWrapper() })
    result.current.mutate({ msId: 'meta-1', strategyId: 'strat-1' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockForceMetaPromote).toHaveBeenCalledWith('meta-1', 'strat-1')
  })
})
