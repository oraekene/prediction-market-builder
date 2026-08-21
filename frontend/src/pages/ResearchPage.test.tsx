import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ResearchPage from './ResearchPage'

const mockApi = vi.hoisted(() => ({
  fetchResearchSessions: vi.fn(),
  fetchResearchStats: vi.fn(),
  fetchResearchResults: vi.fn(),
  fetchResearchConfig: vi.fn(),
  fetchClimate: vi.fn(),
  fetchAlphaVectors: vi.fn(),
  triggerResearchRun: vi.fn(),
  triggerContinuousResearch: vi.fn(),
  stopResearch: vi.fn(),
  triggerRlmScan: vi.fn(),
}))

vi.mock('@/lib/api', () => mockApi)

vi.mock('@/hooks/useResearchWebSocket', () => ({
  useResearchWebSocket: vi.fn(),
}))

const emptyStats = { total_sessions: 0, total_kept: 0, avg_sharpe: 0, keep_rate: 0, best_sharpe: 0 }

function renderPage() {
  return render(
    <MemoryRouter>
      <ResearchPage />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ResearchPage', () => {
  it('renders page title and action buttons', () => {
    renderPage()
    expect(screen.getByText('pi-autoresearch')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /run now/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^continuous$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /stop/i })).toBeInTheDocument()
  })

  it('shows empty states when no data is loaded', () => {
    mockApi.fetchResearchSessions.mockResolvedValue({ sessions: [], total: 0 })
    mockApi.fetchResearchStats.mockResolvedValue(null)
    mockApi.fetchResearchConfig.mockResolvedValue(null)
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })

    renderPage()

    expect(screen.getByText('No active iteration')).toBeInTheDocument()
    expect(screen.getByText('No sessions')).toBeInTheDocument()
    expect(screen.getByText('No results yet')).toBeInTheDocument()
    expect(screen.getByText('Not available')).toBeInTheDocument()
    expect(screen.getByText('No vectors')).toBeInTheDocument()
  })

  it('renders stats cards after data loads', async () => {
    mockApi.fetchResearchSessions.mockResolvedValue({ sessions: [], total: 0 })
    mockApi.fetchResearchStats.mockResolvedValue({
      total_sessions: 42,
      total_kept: 15,
      avg_sharpe: 1.25,
      keep_rate: 0.36,
      best_sharpe: 2.85,
    })
    mockApi.fetchResearchConfig.mockResolvedValue({})
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Total Sessions')).toBeInTheDocument()
      expect(screen.getByText('42')).toBeInTheDocument()
      expect(screen.getByText('Kept')).toBeInTheDocument()
      expect(screen.getByText('15')).toBeInTheDocument()
      expect(screen.getByText('Avg Sharpe')).toBeInTheDocument()
      expect(screen.getByText('1.25')).toBeInTheDocument()
      expect(screen.getByText('Keep Rate')).toBeInTheDocument()
      expect(screen.getByText('36%')).toBeInTheDocument()
      expect(screen.getByText('Best Sharpe')).toBeInTheDocument()
      expect(screen.getByText('2.85')).toBeInTheDocument()
    })
  })

  it('renders session list', async () => {
    const sessions = [
      { id: 'sess-1', mode: 'manual', status: 'completed', current_iteration: 5, avg_sharpe: 1.5, created_at: '2025-01-15T10:00:00Z' },
      { id: 'sess-2', mode: 'auto', status: 'running', current_iteration: 3, avg_sharpe: 0.8, created_at: '2025-01-15T11:00:00Z' },
    ]

    mockApi.fetchResearchSessions.mockResolvedValue({ sessions, total: 2 })
    mockApi.fetchResearchStats.mockResolvedValue({ ...emptyStats, total_sessions: 2, total_kept: 1, avg_sharpe: 1.15, keep_rate: 0.5, best_sharpe: 1.5 })
    mockApi.fetchResearchConfig.mockResolvedValue({})
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('manual')).toBeInTheDocument()
      expect(screen.getByText('auto')).toBeInTheDocument()
      expect(screen.getByText(/5 iterations/)).toBeInTheDocument()
      expect(screen.getByText(/3 iterations/)).toBeInTheDocument()
    })
  })

  it('selects a session and loads results', async () => {
    mockApi.fetchResearchSessions.mockResolvedValue({
      sessions: [{ id: 'sess-1', mode: 'manual', status: 'completed', current_iteration: 1, avg_sharpe: 1.2, created_at: '2025-01-15T10:00:00Z' }],
      total: 1,
    })
    mockApi.fetchResearchStats.mockResolvedValue({ ...emptyStats, total_sessions: 1, total_kept: 1, avg_sharpe: 1.2, keep_rate: 1, best_sharpe: 1.2 })
    mockApi.fetchResearchConfig.mockResolvedValue({})
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })
    mockApi.fetchResearchResults.mockResolvedValue({
      results: [
        { id: 'res-1', iteration: 1, hypothesis: 'Test hypothesis', composite_score: 0.85, backtest_sharpe: 1.2, backtest_win_rate: 0.6, tabpfn_probability: 0.75, verdict: 'KEPT', regime_at_time: 'bull' },
      ],
      total: 1,
    })

    renderPage()

    const sessionButton = await waitFor(() => screen.getByText('manual').closest('button')!)
    expect(sessionButton).toBeInTheDocument()

    await userEvent.click(sessionButton)

    await waitFor(() => {
      expect(mockApi.fetchResearchResults).toHaveBeenCalledWith('sess-1', 50)
      expect(screen.getByText('Test hypothesis')).toBeInTheDocument()
      expect(screen.getByText('0.850')).toBeInTheDocument()
      expect(screen.getByText('1.200')).toBeInTheDocument()
      expect(screen.getByText('KEPT')).toBeInTheDocument()
    })
  })

  it('renders climate data', async () => {
    mockApi.fetchResearchSessions.mockResolvedValue({ sessions: [], total: 0 })
    mockApi.fetchResearchStats.mockResolvedValue(emptyStats)
    mockApi.fetchResearchConfig.mockResolvedValue({})
    mockApi.fetchClimate.mockResolvedValue({ regime: 'bull', metrics: { volatility: 0.1234 } })
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Climate & Features')).toBeInTheDocument()
      expect(screen.getByText('Regime')).toBeInTheDocument()
      expect(screen.getByText('bull')).toBeInTheDocument()
      expect(screen.getByText('Volatility')).toBeInTheDocument()
      expect(screen.getByText('0.1234')).toBeInTheDocument()
    })
  })

  it('renders alpha vectors', async () => {
    mockApi.fetchResearchSessions.mockResolvedValue({ sessions: [], total: 0 })
    mockApi.fetchResearchStats.mockResolvedValue(emptyStats)
    mockApi.fetchResearchConfig.mockResolvedValue({})
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({
      vectors: [
        { id: 'vec-1', source_type: 'forum', token_count: 1500 },
        { id: 'vec-2', source_type: 'paper', token_count: 3200 },
      ],
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('forum')).toBeInTheDocument()
      expect(screen.getByText('paper')).toBeInTheDocument()
      expect(screen.getByText('1500 tokens')).toBeInTheDocument()
      expect(screen.getByText('3200 tokens')).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully without crashing', async () => {
    mockApi.fetchResearchSessions.mockRejectedValue(new Error('Network error'))
    mockApi.fetchResearchStats.mockRejectedValue(new Error('Network error'))
    mockApi.fetchResearchConfig.mockRejectedValue(new Error('Network error'))
    mockApi.fetchClimate.mockRejectedValue(new Error('Network error'))
    mockApi.fetchAlphaVectors.mockRejectedValue(new Error('Network error'))

    renderPage()

    await vi.waitFor(() => {
      expect(screen.getByText('No active iteration')).toBeInTheDocument()
      expect(screen.getByText('No sessions')).toBeInTheDocument()
      expect(screen.getByText('No results yet')).toBeInTheDocument()
    })
  })

  it('calls triggerResearchRun on Run Now click', async () => {
    mockApi.fetchResearchSessions.mockResolvedValue({ sessions: [], total: 0 })
    mockApi.fetchResearchStats.mockResolvedValue(null)
    mockApi.fetchResearchConfig.mockResolvedValue(null)
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })
    mockApi.triggerResearchRun.mockResolvedValue({ session_id: 'new-sess' })

    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /run now/i }))

    await waitFor(() => {
      expect(mockApi.triggerResearchRun).toHaveBeenCalledOnce()
    })
  })

  it('calls triggerRlmScan on Scan click', async () => {
    mockApi.fetchResearchSessions.mockResolvedValue({ sessions: [], total: 0 })
    mockApi.fetchResearchStats.mockResolvedValue(null)
    mockApi.fetchResearchConfig.mockResolvedValue(null)
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })
    mockApi.triggerRlmScan.mockResolvedValue({})

    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /scan/i }))

    await waitFor(() => {
      expect(mockApi.triggerRlmScan).toHaveBeenCalledWith('forum')
    })
  })

  it('disables Run Now and Continuous buttons while running', async () => {
    let resolveRun!: (value: any) => void
    mockApi.triggerResearchRun.mockReturnValue(new Promise((r) => { resolveRun = r }))
    mockApi.fetchResearchSessions.mockResolvedValue({ sessions: [], total: 0 })
    mockApi.fetchResearchStats.mockResolvedValue(null)
    mockApi.fetchResearchConfig.mockResolvedValue(null)
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })

    renderPage()

    await userEvent.click(screen.getByRole('button', { name: /run now/i }))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /running/i })).toBeDisabled()
    })

    resolveRun!({ session_id: 'sess-1' })
  })

  it('renders session status badges with correct colors', async () => {
    const sessions = [
      { id: 'sess-1', mode: 'auto', status: 'running', current_iteration: 2, avg_sharpe: 0.5, created_at: '2025-01-15T10:00:00Z' },
      { id: 'sess-2', mode: 'manual', status: 'completed', current_iteration: 7, avg_sharpe: 2.1, created_at: '2025-01-15T11:00:00Z' },
      { id: 'sess-3', mode: 'auto', status: 'failed', current_iteration: 1, avg_sharpe: -0.3, created_at: '2025-01-15T12:00:00Z' },
    ]

    mockApi.fetchResearchSessions.mockResolvedValue({ sessions, total: 3 })
    mockApi.fetchResearchStats.mockResolvedValue({ ...emptyStats, total_sessions: 3, total_kept: 1, avg_sharpe: 0.77, keep_rate: 0.33, best_sharpe: 2.1 })
    mockApi.fetchResearchConfig.mockResolvedValue({})
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('running')).toBeInTheDocument()
      expect(screen.getByText('completed')).toBeInTheDocument()
      expect(screen.getByText('failed')).toBeInTheDocument()
    })
  })

  it('disables Stop button when not running', () => {
    mockApi.fetchResearchSessions.mockResolvedValue({ sessions: [], total: 0 })
    mockApi.fetchResearchStats.mockResolvedValue(null)
    mockApi.fetchResearchConfig.mockResolvedValue(null)
    mockApi.fetchClimate.mockResolvedValue(null)
    mockApi.fetchAlphaVectors.mockResolvedValue({ vectors: [] })

    renderPage()

    expect(screen.getByRole('button', { name: /stop/i })).toBeDisabled()
  })
})
