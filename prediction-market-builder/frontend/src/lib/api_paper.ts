import type { PaperWallet, PaperOrderItem, PaperOrderRequest, PaperOrderResponse, PaperPerformance, PerformanceMetricResponse, StrategyComparison } from '@/types/paperTrading'
import { apiFetch } from './auth'

export async function fetchPaperWallet(userId = 'default'): Promise<PaperWallet> {
  const res = await apiFetch(`/api/paper/wallet?user_id=${userId}`)
  if (!res.ok) throw new Error('Failed to fetch paper wallet')
  return res.json()
}

export async function resetPaperWallet(userId = 'default'): Promise<{ success: boolean; initial_balance: number; current_balance: number }> {
  const res = await apiFetch(`/api/paper/wallet/reset?user_id=${userId}`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to reset wallet')
  return res.json()
}

export async function placePaperOrder(data: PaperOrderRequest): Promise<PaperOrderResponse> {
  const res = await apiFetch('/api/paper/orders', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to place order')
  return res.json()
}

export async function fetchPaperOrders(walletId?: string, status?: string): Promise<{ orders: PaperOrderItem[]; total: number }> {
  const params = new URLSearchParams()
  if (walletId) params.set('wallet_id', walletId)
  if (status) params.set('status', status)
  const res = await apiFetch(`/api/paper/orders?${params.toString()}`)
  if (!res.ok) throw new Error('Failed to fetch orders')
  return res.json()
}

export async function cancelPaperOrder(orderId: string): Promise<{ success: boolean }> {
  const res = await apiFetch(`/api/paper/orders/${orderId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to cancel order')
  return res.json()
}

export async function fetchPaperPerformance(strategyId?: string, userId = 'default'): Promise<PaperPerformance> {
  const params = new URLSearchParams()
  if (strategyId) params.set('strategy_id', strategyId)
  params.set('user_id', userId)
  const res = await apiFetch(`/api/paper/performance?${params.toString()}`)
  if (!res.ok) throw new Error('Failed to fetch performance')
  return res.json()
}

export async function comparePaperStrategies(strategyIds: string[]): Promise<StrategyComparison> {
  const res = await apiFetch(`/api/paper/compare?strategy_ids=${strategyIds.join(',')}`)
  if (!res.ok) throw new Error('Failed to compare strategies')
  return res.json()
}

export async function syncPaperResolutions(resolutions: { market_id: string; platform: string; outcome: string }[]): Promise<{ updated: number; resolutions: number }> {
  const res = await apiFetch('/api/paper/sync-resolutions', {
    method: 'POST',
    body: JSON.stringify({ resolutions }),
  })
  if (!res.ok) throw new Error('Failed to sync resolutions')
  return res.json()
}

export async function fetchPaperMetric(metric: string, window = 0, userId = 'default'): Promise<PerformanceMetricResponse> {
  const res = await apiFetch(`/api/paper/metrics/${metric}?user_id=${userId}&window=${window}`)
  if (!res.ok) throw new Error('Failed to fetch metric')
  return res.json()
}
