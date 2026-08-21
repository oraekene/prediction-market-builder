import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import AnalyticsPage from './AnalyticsPage'

const mockFetchAnalyticsSummary = vi.fn()
const mockFetchAnalyticsBacktests = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchAnalyticsSummary: (...args: any[]) => mockFetchAnalyticsSummary(...args),
  fetchAnalyticsBacktests: (...args: any[]) => mockFetchAnalyticsBacktests(...args),
}))

vi.mock('@/components/analytics/RiskDashboard', () => ({
  default: () => <div>Risk Dashboard</div>,
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
  }
}

function renderPage() {
  return render(<AnalyticsPage />, { wrapper: createWrapper() })
}

const mockSummary = {
  total_trades: 150,
  win_rate: 62.5,
  winning_trades: 93,
  total_pnl: 12500.50,
}

const mockBacktests = {
  backtests: [
    { name: 'Momentum Strategy', trades: [1, 2, 3] },
    { name: 'Mean Reversion', trades: [1, 2] },
  ],
}

describe('AnalyticsPage', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('shows loading state', () => {
    mockFetchAnalyticsSummary.mockReturnValue(new Promise(() => {}))
    mockFetchAnalyticsBacktests.mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading analytics...')).toBeInTheDocument()
  })

  it('renders summary cards when data loads', async () => {
    mockFetchAnalyticsSummary.mockResolvedValue(mockSummary)
    mockFetchAnalyticsBacktests.mockResolvedValue(mockBacktests)
    renderPage()
    await waitFor(() => expect(screen.getByText('150')).toBeInTheDocument())
    expect(screen.getByText('62.5%')).toBeInTheDocument()
    expect(screen.getByText('93')).toBeInTheDocument()
    expect(screen.getByText('$12500.50')).toBeInTheDocument()
  })

  it('renders backtests list', async () => {
    mockFetchAnalyticsSummary.mockResolvedValue(mockSummary)
    mockFetchAnalyticsBacktests.mockResolvedValue(mockBacktests)
    renderPage()
    await waitFor(() => expect(screen.getByText('Momentum Strategy')).toBeInTheDocument())
    expect(screen.getByText('Mean Reversion')).toBeInTheDocument()
  })

  it('shows empty backtests message', async () => {
    mockFetchAnalyticsSummary.mockResolvedValue(mockSummary)
    mockFetchAnalyticsBacktests.mockResolvedValue({ backtests: [] })
    renderPage()
    await waitFor(() => expect(screen.getByText('No backtests recorded yet. Run a strategy to see results here.')).toBeInTheDocument())
  })

  it('renders RiskDashboard component', async () => {
    mockFetchAnalyticsSummary.mockResolvedValue(mockSummary)
    mockFetchAnalyticsBacktests.mockResolvedValue(mockBacktests)
    renderPage()
    await waitFor(() => expect(screen.getByText('Risk Dashboard')).toBeInTheDocument())
  })

  it('highlights positive P&L in green', async () => {
    mockFetchAnalyticsSummary.mockResolvedValue({ ...mockSummary, total_pnl: 5000 })
    mockFetchAnalyticsBacktests.mockResolvedValue(mockBacktests)
    renderPage()
    await waitFor(() => {
      const pnl = screen.getByText('$5000.00')
      expect(pnl.className).toContain('green')
    })
  })

  it('handles missing summary gracefully', async () => {
    mockFetchAnalyticsSummary.mockResolvedValue(null)
    mockFetchAnalyticsBacktests.mockResolvedValue(mockBacktests)
    renderPage()
    await waitFor(() => expect(screen.getByText('Analytics')).toBeInTheDocument())
    expect(screen.queryByText('Total Trades')).not.toBeInTheDocument()
  })
})
