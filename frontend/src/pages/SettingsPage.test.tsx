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
      expect(screen.getByText('Polymarket API Key (api_key:secret)')).toBeInTheDocument()
      expect(screen.getByText('Kalshi Private Key')).toBeInTheDocument()
      expect(screen.getByText('Drift API Key')).toBeInTheDocument()
    })

    it('shows Save Keys button', () => {
      renderPage()
      expect(screen.getByRole('button', { name: 'Save Keys' })).toBeInTheDocument()
    })

    it('shows Saved feedback after saving with empty keys (no-op save)', async () => {
      renderPage()
      const saveBtn = screen.getByRole('button', { name: 'Save Keys' })
      await userEvent.click(saveBtn)
      expect(screen.getByText('Saved')).toBeInTheDocument()
    })

    it('saves keys via the encrypted server endpoint', async () => {
      mockApiFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) })
      renderPage()
      await userEvent.type(screen.getByPlaceholderText('Enter your Polymarket API key'), 'pm-key')
      await userEvent.click(screen.getByRole('button', { name: 'Save Keys' }))
      await waitFor(() => {
        expect(mockApiFetch).toHaveBeenCalledWith('/api/auth/keys', expect.objectContaining({ method: 'PUT' }))
      })
    })
  })

  describe('Trading Mode section', () => {
    it('renders Paper Trading and Live Trading buttons', () => {
      renderPage()
      expect(screen.getByRole('button', { name: 'Paper Trading' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Live Trading' })).toBeInTheDocument()
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
    it('renders backend and exchange status from real health', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok' }) }))
      renderPage()
      await waitFor(() => expect(screen.getByText('Online')).toBeInTheDocument())
      expect(screen.getByText('Exchange connections:')).toBeInTheDocument()
      vi.unstubAllGlobals()
    })

    it('shows Offline when backend health fails', async () => {
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')))
      renderPage()
      await waitFor(() => expect(screen.getByText('Offline')).toBeInTheDocument())
      vi.unstubAllGlobals()
    })
  })
})
