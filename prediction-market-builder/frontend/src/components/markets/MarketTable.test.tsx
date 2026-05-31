import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import MarketTable from './MarketTable'

const mockFetchMarkets = vi.fn()

vi.mock('@/lib/api', () => ({ fetchMarkets: (...args: any[]) => mockFetchMarkets(...args) }))

const marketsData = {
  markets: [
    { platform: 'polymarket', platform_market_id: 'pm-1', title: 'BTC to $100k', category: 'Crypto', current_odds: 0.65, volume: 5_000_000, close_time: '2026-12-31T23:59:59Z' },
    { platform: 'kalshi', platform_market_id: 'kl-1', title: 'Fed Rate Cut', category: 'Economy', current_odds: 0.35, volume: 2_000_000, close_time: '2026-06-30T23:59:59Z' },
    { platform: 'polymarket', platform_market_id: 'pm-2', title: 'Election 2026', category: 'Politics', current_odds: 0.72, volume: 10_000_000, close_time: null },
  ],
}

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
  }
}

function renderPage() {
  return render(<MarketTable />, { wrapper: createWrapper() })
}

describe('MarketTable', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('shows loading state', () => {
    mockFetchMarkets.mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading markets...')).toBeInTheDocument()
  })

  it('shows error state', async () => {
    mockFetchMarkets.mockRejectedValue(new Error('API error'))
    renderPage()
    await waitFor(() => expect(screen.getByText('Error loading markets')).toBeInTheDocument())
  })

  it('renders market data', async () => {
    mockFetchMarkets.mockResolvedValue(marketsData)
    renderPage()
    await waitFor(() => expect(screen.getByText('BTC to $100k')).toBeInTheDocument())
    expect(screen.getByText('Fed Rate Cut')).toBeInTheDocument()
    expect(screen.getByText('Election 2026')).toBeInTheDocument()
  })

  it('filters by category', async () => {
    mockFetchMarkets.mockResolvedValue(marketsData)
    renderPage()
    await waitFor(() => expect(screen.getByText('BTC to $100k')).toBeInTheDocument())
    await userEvent.click(screen.getAllByText('Crypto')[0])
    expect(screen.getByText('BTC to $100k')).toBeInTheDocument()
    expect(screen.queryByText('Fed Rate Cut')).not.toBeInTheDocument()
    expect(screen.queryByText('Election 2026')).not.toBeInTheDocument()
  })

  it('filters by search query', async () => {
    mockFetchMarkets.mockResolvedValue(marketsData)
    renderPage()
    await waitFor(() => expect(screen.getByText('BTC to $100k')).toBeInTheDocument())
    const searchInput = screen.getByPlaceholderText('Search markets...')
    await userEvent.type(searchInput, 'fed')
    expect(screen.queryByText('BTC to $100k')).not.toBeInTheDocument()
    expect(screen.getByText('Fed Rate Cut')).toBeInTheDocument()
  })

  it('shows empty state when no markets match filters', async () => {
    mockFetchMarkets.mockResolvedValue(marketsData)
    renderPage()
    await waitFor(() => expect(screen.getByText('BTC to $100k')).toBeInTheDocument())
    const searchInput = screen.getByPlaceholderText('Search markets...')
    await userEvent.type(searchInput, 'zzzzz')
    expect(screen.getByText('No markets found')).toBeInTheDocument()
    expect(screen.getByText('Try a different search or category')).toBeInTheDocument()
  })

  it('renders quick stats', async () => {
    mockFetchMarkets.mockResolvedValue(marketsData)
    renderPage()
    await waitFor(() => expect(screen.getByText('Total Markets')).toBeInTheDocument())
    expect(screen.getByText('Avg Odds')).toBeInTheDocument()
    expect(screen.getByText('Total Volume')).toBeInTheDocument()
  })

  it('renders all category filters', async () => {
    mockFetchMarkets.mockResolvedValue(marketsData)
    renderPage()
    await waitFor(() => expect(screen.getByText('All')).toBeInTheDocument())
    expect(screen.getAllByText('Politics').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Economy').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Crypto').length).toBeGreaterThan(0)
    expect(screen.getByText('Sports')).toBeInTheDocument()
    expect(screen.getByText('Science')).toBeInTheDocument()
  })
})
