import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { usePortfolio } from './usePortfolio'

const mockFetchPortfolio = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchPortfolio: (...args: any[]) => mockFetchPortfolio(...args),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('usePortfolio', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns portfolio data', async () => {
    const data = { total_value: 50000, available: 30000, positions: [] }
    mockFetchPortfolio.mockResolvedValue(data)
    const { result } = renderHook(() => usePortfolio(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(data)
  })
})
