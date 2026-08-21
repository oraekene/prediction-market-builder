import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import {
  useSafeWallets, useCreateSafeWallet, useSafeWalletBalance,
  useTransferToSafe, useWithdrawalHistory, useWithdrawalStrategies,
  useCreateWithdrawalStrategy, useUpdateWithdrawalStrategy,
  useDeleteWithdrawalStrategy, useEvaluateWithdrawalStrategy,
  useToggleWithdrawalStrategy,
} from './useWithdrawal'

const mockApiFetch = vi.fn()

vi.mock('@/lib/auth', () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

function okResponse(data: any) {
  return { ok: true, json: () => Promise.resolve(data) } as Response
}

function errorResponse() {
  return { ok: false } as Response
}

describe('useSafeWallets', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns safe wallets', async () => {
    const wallets = [{ id: 'safe-1', name: 'Test', balance: 50000, protected_amount: 30000, status: 'active' }]
    mockApiFetch.mockResolvedValue(okResponse(wallets))
    const { result } = renderHook(() => useSafeWallets(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(wallets)
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/wallets')
  })

  it('handles fetch error', async () => {
    mockApiFetch.mockResolvedValue(errorResponse())
    const { result } = renderHook(() => useSafeWallets(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe('useCreateSafeWallet', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls apiFetch POST on mutation', async () => {
    mockApiFetch.mockResolvedValue(okResponse({ id: 'safe-2' }))
    const { result } = renderHook(() => useCreateSafeWallet(), { wrapper: createWrapper() })
    result.current.mutate({ name: 'New', currency: 'USD' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/wallets', {
      method: 'POST', body: JSON.stringify({ name: 'New', currency: 'USD' }),
    })
  })
})

describe('useSafeWalletBalance', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns balance', async () => {
    mockApiFetch.mockResolvedValue(okResponse({ balance: 50000 }))
    const { result } = renderHook(() => useSafeWalletBalance(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/balance')
  })
})

describe('useTransferToSafe', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls apiFetch POST on mutation', async () => {
    mockApiFetch.mockResolvedValue(okResponse({ success: true }))
    const { result } = renderHook(() => useTransferToSafe(), { wrapper: createWrapper() })
    result.current.mutate({ amount: 1000, currency: 'USD', source: 'exchange' })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/transfer', {
      method: 'POST', body: JSON.stringify({ amount: 1000, currency: 'USD', source: 'exchange' }),
    })
  })
})

describe('useWithdrawalHistory', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns history', async () => {
    mockApiFetch.mockResolvedValue(okResponse([]))
    const { result } = renderHook(() => useWithdrawalHistory(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/history')
  })
})

describe('useWithdrawalStrategies', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns withdrawal strategies', async () => {
    mockApiFetch.mockResolvedValue(okResponse([]))
    const { result } = renderHook(() => useWithdrawalStrategies(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/strategies')
  })
})

describe('useCreateWithdrawalStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls apiFetch POST on mutation', async () => {
    mockApiFetch.mockResolvedValue(okResponse({ id: 'ws-1' }))
    const payload = { name: 'Test Strategy', description: 'A test', steps: [], safe_wallet_id: 'safe-1' }
    const { result } = renderHook(() => useCreateWithdrawalStrategy(), { wrapper: createWrapper() })
    result.current.mutate(payload)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/strategies', {
      method: 'POST', body: JSON.stringify(payload),
    })
  })
})

describe('useUpdateWithdrawalStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls apiFetch PUT on mutation', async () => {
    mockApiFetch.mockResolvedValue(okResponse({}))
    const { result } = renderHook(() => useUpdateWithdrawalStrategy(), { wrapper: createWrapper() })
    result.current.mutate({ id: 'ws-1', data: { name: 'Updated' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/strategies/ws-1', {
      method: 'PUT', body: JSON.stringify({ name: 'Updated' }),
    })
  })
})

describe('useDeleteWithdrawalStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls apiFetch DELETE on mutation', async () => {
    mockApiFetch.mockResolvedValue(okResponse({}))
    const { result } = renderHook(() => useDeleteWithdrawalStrategy(), { wrapper: createWrapper() })
    result.current.mutate('ws-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/strategies/ws-1', { method: 'DELETE' })
  })
})

describe('useEvaluateWithdrawalStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls apiFetch POST /evaluate on mutation', async () => {
    mockApiFetch.mockResolvedValue(okResponse({ score: 85 }))
    const { result } = renderHook(() => useEvaluateWithdrawalStrategy(), { wrapper: createWrapper() })
    result.current.mutate('ws-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/strategies/ws-1/evaluate', { method: 'POST' })
  })
})

describe('useToggleWithdrawalStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls apiFetch POST /toggle on mutation', async () => {
    mockApiFetch.mockResolvedValue(okResponse({ active: false }))
    const { result } = renderHook(() => useToggleWithdrawalStrategy(), { wrapper: createWrapper() })
    result.current.mutate('ws-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApiFetch).toHaveBeenCalledWith('/api/withdrawal/strategies/ws-1/toggle', { method: 'POST' })
  })
})
