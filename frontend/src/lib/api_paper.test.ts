import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchPaperWallet, resetPaperWallet, placePaperOrder,
  fetchPaperOrders, cancelPaperOrder, fetchPaperPerformance,
  comparePaperStrategies, syncPaperResolutions, fetchPaperMetric,
} from './api_paper'

const mockApiFetch = vi.hoisted(() => vi.fn())

vi.mock('./auth', () => ({
  apiFetch: mockApiFetch,
}))

function mockResponse(data: any, ok = true) {
  return { ok, json: vi.fn().mockResolvedValue(data) }
}

beforeEach(() => {
  mockApiFetch.mockReset()
})

describe('fetchPaperWallet', () => {
  it('calls GET /api/paper/wallet with user_id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ cash_balance: 10000 }))
    const result = await fetchPaperWallet('user-1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/paper/wallet?user_id=user-1')
    expect(result).toEqual({ cash_balance: 10000 })
  })

  it('defaults to "default" user', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchPaperWallet()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/paper/wallet?user_id=default')
  })
})

describe('resetPaperWallet', () => {
  it('calls POST /api/paper/wallet/reset', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ success: true, initial_balance: 10000, current_balance: 10000 }))
    const result = await resetPaperWallet('user-1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/paper/wallet/reset?user_id=user-1',
      { method: 'POST' },
    )
    expect(result.success).toBe(true)
  })
})

describe('placePaperOrder', () => {
  it('calls POST /api/paper/orders with body', async () => {
    const order = { wallet_id: 'w-1', market_id: 'm1', platform: 'polymarket' as const, side: 'buy' as const, price: 0.65, amount: 100 }
    mockApiFetch.mockResolvedValue(mockResponse({ order_id: 'o1' }))
    const result = await placePaperOrder(order)
    expect(mockApiFetch).toHaveBeenCalledWith('/api/paper/orders', {
      method: 'POST',
      body: JSON.stringify(order),
    })
    expect(result).toEqual({ order_id: 'o1' })
  })
})

describe('fetchPaperOrders', () => {
  it('calls GET /api/paper/orders with params', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ orders: [], total: 0 }))
    await fetchPaperOrders('wallet-1', 'filled')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/paper/orders?wallet_id=wallet-1&status=filled',
    )
  })

  it('works without params', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ orders: [], total: 0 }))
    await fetchPaperOrders()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/paper/orders?')
  })
})

describe('cancelPaperOrder', () => {
  it('calls DELETE /api/paper/orders/:id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ success: true }))
    const result = await cancelPaperOrder('order-1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/paper/orders/order-1', {
      method: 'DELETE',
    })
    expect(result.success).toBe(true)
  })
})

describe('fetchPaperPerformance', () => {
  it('calls GET /api/paper/performance with params', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ total_trades: 25 }))
    await fetchPaperPerformance('strategy-1', 'user-1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/paper/performance?strategy_id=strategy-1&user_id=user-1',
    )
  })
})

describe('comparePaperStrategies', () => {
  it('calls GET /api/paper/compare with comma-separated IDs', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await comparePaperStrategies(['s1', 's2', 's3'])
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/paper/compare?strategy_ids=s1,s2,s3',
    )
  })
})

describe('syncPaperResolutions', () => {
  it('calls POST /api/paper/sync-resolutions with body', async () => {
    const resolutions = [{ market_id: 'm1', platform: 'polymarket', outcome: 'YES' }]
    mockApiFetch.mockResolvedValue(mockResponse({ updated: 1, resolutions: 1 }))
    const result = await syncPaperResolutions(resolutions)
    expect(mockApiFetch).toHaveBeenCalledWith('/api/paper/sync-resolutions', {
      method: 'POST',
      body: JSON.stringify({ resolutions }),
    })
    expect(result.updated).toBe(1)
  })
})

describe('fetchPaperMetric', () => {
  it('calls GET /api/paper/metrics/:metric', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchPaperMetric('sharpe', 50, 'user-1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/paper/metrics/sharpe?user_id=user-1&window=50',
    )
  })
})
