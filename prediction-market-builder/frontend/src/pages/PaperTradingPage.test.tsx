import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import PaperTradingPage from './PaperTradingPage'

vi.mock('@/components/paper_trading/PaperTradingDashboard', () => ({
  default: () => <div>Paper Trading Dashboard Content</div>,
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
  }
}

describe('PaperTradingPage', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders PaperTradingDashboard', () => {
    render(<PaperTradingPage />, { wrapper: createWrapper() })
    expect(screen.getByText('Paper Trading Dashboard Content')).toBeInTheDocument()
  })
})
