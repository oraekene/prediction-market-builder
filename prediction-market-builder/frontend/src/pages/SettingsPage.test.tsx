import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import SettingsPage from './SettingsPage'

const mockApiFetch = vi.fn()

vi.mock('@/lib/auth', () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
  getToken: () => 'fake-token',
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'a@b.com' } }),
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
  }
}

function renderPage() {
  return render(<SettingsPage />, { wrapper: createWrapper() })
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders all sections', () => {
    renderPage()
    expect(screen.getByText('Profile')).toBeInTheDocument()
    expect(screen.getByText('Exchange API Keys')).toBeInTheDocument()
    expect(screen.getByText('Trading Mode')).toBeInTheDocument()
    expect(screen.getByText('Safety Limits')).toBeInTheDocument()
    expect(screen.getByText('Connection Status')).toBeInTheDocument()
  })

  describe('Profile section', () => {
    it('renders email and optional display name', () => {
      renderPage()
      expect(screen.getByText('a@b.com')).toBeInTheDocument()
    })
  })

  describe('Exchange API Keys section', () => {
    it('renders API key inputs', () => {
      renderPage()
      expect(screen.getByText('Polymarket API Key')).toBeInTheDocument()
      expect(screen.getByText('Kalshi API Key')).toBeInTheDocument()
    })

    it('shows Save Keys button', () => {
      renderPage()
      expect(screen.getByText('Save Keys')).toBeInTheDocument()
    })

    it('shows Saved feedback after saving', async () => {
      renderPage()
      const saveBtn = screen.getByText('Save Keys')
      await userEvent.click(saveBtn)
      expect(screen.getByText('Saved')).toBeInTheDocument()
    })
  })

  describe('Trading Mode section', () => {
    it('renders Paper Trading and Live Trading buttons', () => {
      renderPage()
      expect(screen.getByText('Paper Trading')).toBeInTheDocument()
      expect(screen.getByText('Live Trading')).toBeInTheDocument()
    })
  })

  describe('Safety Limits section', () => {
    it('renders max session loss input', () => {
      renderPage()
      expect(screen.getByText('Max Session Loss ($)')).toBeInTheDocument()
      const input = screen.getByDisplayValue('100')
      expect(input).toBeInTheDocument()
    })
  })

  describe('Connection Status section', () => {
    it('renders backend and exchange status', () => {
      renderPage()
      expect(screen.getByText('Backend:')).toBeInTheDocument()
      expect(screen.getByText('Online')).toBeInTheDocument()
      expect(screen.getByText('Exchange connections:')).toBeInTheDocument()
    })
  })
})
