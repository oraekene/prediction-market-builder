import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import WithdrawalPage from './WithdrawalPage'

const mockApiFetch = vi.fn()

vi.mock('@/lib/auth', () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
}))

const mockWallets = [
  { id: 'w1', name: 'Main Wallet', balance: 50000, protected_amount: 30000, status: 'active', created_at: '2026-01-01T00:00:00Z' },
]

const mockStrategies = [
  { id: 'ws-1', name: 'Tax Harvesting', description: 'Tax loss harvesting strategy', active: true, steps: [], safe_wallet_id: 'w1', created_at: '2026-01-15T00:00:00Z' },
  { id: 'ws-2', name: 'Dollar Cost Avg', description: null, active: false, steps: [], safe_wallet_id: null, created_at: '2026-02-01T00:00:00Z' },
]

const mockHistory = [
  { id: 'h1', amount: 1000, currency: 'USDC', status: 'completed', created_at: '2026-01-20T00:00:00Z' },
]

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
  }
}

function okResponse(data: any) {
  return { ok: true, json: () => Promise.resolve(data) } as Response
}

describe('WithdrawalPage', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders page title and new strategy button', async () => {
    mockApiFetch.mockResolvedValue(okResponse([]))
    render(<WithdrawalPage />, { wrapper: createWrapper() })
    await waitFor(() => expect(screen.getByText('Withdrawal Strategy Builder')).toBeInTheDocument())
    expect(screen.getByText('+ New Strategy')).toBeInTheDocument()
  })

  it('shows loading state for strategies', () => {
    mockApiFetch.mockReturnValue(new Promise(() => {}))
    render(<WithdrawalPage />, { wrapper: createWrapper() })
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('shows empty state for strategies', async () => {
    mockApiFetch.mockResolvedValue(okResponse([]))
    render(<WithdrawalPage />, { wrapper: createWrapper() })
    await waitFor(() => expect(screen.getByText('No strategies yet.')).toBeInTheDocument())
  })

  it('renders strategy list', async () => {
    mockApiFetch.mockImplementation((url: string) => {
      if (url.includes('/wallets')) return Promise.resolve(okResponse(mockWallets))
      if (url.includes('/strategies')) return Promise.resolve(okResponse(mockStrategies))
      if (url.includes('/history')) return Promise.resolve(okResponse(mockHistory))
      if (url.includes('/balance')) return Promise.resolve(okResponse({ balance: 100000 }))
      return Promise.resolve(okResponse(null))
    })
    render(<WithdrawalPage />, { wrapper: createWrapper() })
    await waitFor(() => expect(screen.getByText('Tax Harvesting')).toBeInTheDocument())
    expect(screen.getByText('Dollar Cost Avg')).toBeInTheDocument()
  })

  it('selects a strategy and shows editor fields', async () => {
    mockApiFetch.mockImplementation((url: string) => {
      if (url.includes('/wallets')) return Promise.resolve(okResponse(mockWallets))
      if (url.includes('/strategies')) return Promise.resolve(okResponse(mockStrategies))
      if (url.includes('/history')) return Promise.resolve(okResponse(mockHistory))
      if (url.includes('/balance')) return Promise.resolve(okResponse({ balance: 100000 }))
      return Promise.resolve(okResponse(null))
    })
    render(<WithdrawalPage />, { wrapper: createWrapper() })
    await waitFor(() => expect(screen.getByText('Tax Harvesting')).toBeInTheDocument())
    await userEvent.click(screen.getByText('Tax Harvesting'))
    await waitFor(() => {
      const nameInput = screen.getByDisplayValue('Tax Harvesting')
      expect(nameInput).toBeInTheDocument()
    })
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('Save Strategy')).toBeInTheDocument()
    expect(screen.getByText('Test Strategy')).toBeInTheDocument()
    expect(screen.getByText('Delete')).toBeInTheDocument()
  })

  it('toggles safe wallets section', async () => {
    mockApiFetch.mockResolvedValue(okResponse([]))
    render(<WithdrawalPage />, { wrapper: createWrapper() })
    await waitFor(() => expect(screen.getByText(/Safe Wallets/)).toBeInTheDocument())
    await userEvent.click(screen.getByText(/Safe Wallets/))
    expect(screen.getByText('Create Safe Wallet')).toBeInTheDocument()
  })

  it('can create new empty strategy', async () => {
    mockApiFetch.mockResolvedValue(okResponse([]))
    render(<WithdrawalPage />, { wrapper: createWrapper() })
    await waitFor(() => expect(screen.getByText('Withdrawal Strategy Builder')).toBeInTheDocument())
    await userEvent.click(screen.getByText('+ New Strategy'))
    await waitFor(() => expect(screen.getByText('Steps')).toBeInTheDocument())
  })
})
