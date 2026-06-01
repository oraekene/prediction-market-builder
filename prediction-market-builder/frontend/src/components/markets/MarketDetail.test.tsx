import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import MarketDetail from './MarketDetail'

const mockFetchMarket = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchMarket: (...args: any[]) => mockFetchMarket(...args),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('MarketDetail', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('shows loading state', () => {
    mockFetchMarket.mockReturnValue(new Promise(() => {}))
    render(<MarketDetail marketId="test-123" />, { wrapper: createWrapper() })
    expect(screen.getByText('Loading market...')).toBeTruthy()
  })

  it('shows error state when fetch fails', async () => {
    mockFetchMarket.mockRejectedValue(new Error('Not found'))
    render(<MarketDetail marketId="test-123" />, { wrapper: createWrapper() })
    expect(await screen.findByText('Failed to load market')).toBeTruthy()
  })

  it('renders market data when loaded', async () => {
    mockFetchMarket.mockResolvedValue({
      id: 'test-123',
      title: 'Test Market',
      platform: 'polymarket',
      category: 'Politics',
      current_odds: 0.65,
      volume: 50000,
      close_time: '2025-06-01T00:00:00Z',
    })
    render(<MarketDetail marketId="test-123" />, { wrapper: createWrapper() })
    expect(await screen.findByText('Test Market')).toBeTruthy()
    expect(screen.getByText('polymarket')).toBeTruthy()
    expect(screen.getByText('Politics')).toBeTruthy()
  })
})
