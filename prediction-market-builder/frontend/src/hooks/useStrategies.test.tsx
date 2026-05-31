import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useStrategies, useStrategy, useCreateStrategy, useUpdateStrategy, useDeleteStrategy } from './useStrategies'
import { createMockStrategy, createMockStrategies } from '@/test/mocks'

const mockFetchStrategies = vi.fn()
const mockFetchStrategy = vi.fn()
const mockCreateStrategy = vi.fn()
const mockUpdateStrategy = vi.fn()
const mockDeleteStrategy = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchStrategies: (...args: any[]) => mockFetchStrategies(...args),
  fetchStrategy: (...args: any[]) => mockFetchStrategy(...args),
  createStrategy: (...args: any[]) => mockCreateStrategy(...args),
  updateStrategy: (...args: any[]) => mockUpdateStrategy(...args),
  deleteStrategy: (...args: any[]) => mockDeleteStrategy(...args),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('useStrategies', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns strategies list', async () => {
    const strategies = createMockStrategies(3)
    mockFetchStrategies.mockResolvedValue(strategies)
    const { result } = renderHook(() => useStrategies(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(strategies)
  })
})

describe('useStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns a single strategy', async () => {
    const strategy = createMockStrategy()
    mockFetchStrategy.mockResolvedValue(strategy)
    const { result } = renderHook(() => useStrategy('strategy-1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(strategy)
  })

  it('is disabled when id is empty', () => {
    const { result } = renderHook(() => useStrategy(''), { wrapper: createWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useCreateStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls createStrategy on mutation', async () => {
    const newStrategy = createMockStrategy()
    mockCreateStrategy.mockResolvedValue(newStrategy)
    const { result } = renderHook(() => useCreateStrategy(), { wrapper: createWrapper() })
    result.current.mutate(newStrategy)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockCreateStrategy).toHaveBeenCalledWith(newStrategy, expect.any(Object))
  })
})

describe('useUpdateStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls updateStrategy on mutation', async () => {
    mockUpdateStrategy.mockResolvedValue(undefined)
    const { result } = renderHook(() => useUpdateStrategy(), { wrapper: createWrapper() })
    result.current.mutate({ id: 'strategy-1', data: { name: 'Updated' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockUpdateStrategy).toHaveBeenCalledWith('strategy-1', { name: 'Updated' })
  })
})

describe('useDeleteStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls deleteStrategy on mutation', async () => {
    mockDeleteStrategy.mockResolvedValue(undefined)
    const { result } = renderHook(() => useDeleteStrategy(), { wrapper: createWrapper() })
    result.current.mutate('strategy-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockDeleteStrategy).toHaveBeenCalledWith('strategy-1', expect.any(Object))
  })
})
