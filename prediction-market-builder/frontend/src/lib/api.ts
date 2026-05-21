import type { RiskSummary, VaRBreakdown, CorrelationData, DrawdownMetrics, PortfolioRisk } from '@/types/risk'

const BASE_URL = '/api'

export async function fetchMarkets(params?: Record<string, string>): Promise<{ markets: any[]; total: number }> {
  const searchParams = new URLSearchParams(params)
  const res = await fetch(`${BASE_URL}/markets?${searchParams}`)
  if (!res.ok) throw new Error('Failed to fetch markets')
  return res.json()
}

export async function fetchMarket(id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/markets/${id}`)
  if (!res.ok) throw new Error('Market not found')
  return res.json()
}

export async function fetchStrategies(): Promise<any> {
  const res = await fetch(`${BASE_URL}/strategies`)
  if (!res.ok) throw new Error('Failed to fetch strategies')
  return res.json()
}

export async function createStrategy(data: any): Promise<any> {
  const res = await fetch(`${BASE_URL}/strategies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create strategy')
  return res.json()
}

export async function fetchPortfolio(): Promise<any> {
  const res = await fetch(`${BASE_URL}/portfolio`)
  if (!res.ok) throw new Error('Failed to fetch portfolio')
  return res.json()
}

export async function fetchAnalyticsSummary(): Promise<any> {
  const res = await fetch(`${BASE_URL}/analytics/summary`)
  if (!res.ok) throw new Error('Failed to fetch analytics')
  return res.json()
}

export async function fetchAnalyticsBacktests(): Promise<any> {
  const res = await fetch(`${BASE_URL}/analytics/backtests`)
  if (!res.ok) throw new Error('Failed to fetch backtests')
  return res.json()
}

export async function triggerResearchRun(strategyId?: string, preset = 'sharpe_max'): Promise<any> {
  const params = new URLSearchParams()
  if (strategyId) params.set('strategy_id', strategyId)
  params.set('preset', preset)
  const res = await fetch(`${BASE_URL}/research/run?${params}`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to trigger research')
  return res.json()
}

export async function triggerContinuousResearch(strategyId?: string, preset = 'sharpe_max'): Promise<any> {
  const params = new URLSearchParams()
  if (strategyId) params.set('strategy_id', strategyId)
  params.set('preset', preset)
  const res = await fetch(`${BASE_URL}/research/run-continuous?${params}`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to start continuous research')
  return res.json()
}

export async function stopResearch(sessionId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/research/stop?session_id=${sessionId}`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to stop research')
  return res.json()
}

export async function createResearchSession(strategyId?: string, mode = 'manual', preset = 'sharpe_max'): Promise<any> {
  const params = new URLSearchParams()
  if (strategyId) params.set('strategy_id', strategyId)
  params.set('mode', mode)
  params.set('preset', preset)
  const res = await fetch(`${BASE_URL}/research/sessions?${params}`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to create session')
  return res.json()
}

export async function fetchResearchSessions(): Promise<{ sessions: any[]; total: number }> {
  const res = await fetch(`${BASE_URL}/research/sessions`)
  if (!res.ok) throw new Error('Failed to fetch sessions')
  return res.json()
}

export async function fetchResearchSession(id: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/research/sessions/${id}`)
  if (!res.ok) throw new Error('Session not found')
  return res.json()
}

export async function fetchResearchResults(sessionId: string, limit = 50): Promise<{ results: any[]; total: number }> {
  const res = await fetch(`${BASE_URL}/research/sessions/${sessionId}/results?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch results')
  return res.json()
}

export async function fetchResearchStats(): Promise<any> {
  const res = await fetch(`${BASE_URL}/research/stats`)
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export async function fetchResearchConfig(): Promise<any> {
  const res = await fetch(`${BASE_URL}/research/config`)
  if (!res.ok) throw new Error('Failed to fetch config')
  return res.json()
}

export async function updateResearchConfig(params: Record<string, string>): Promise<any> {
  const searchParams = new URLSearchParams(params)
  const res = await fetch(`${BASE_URL}/research/config?${searchParams}`, { method: 'PUT' })
  if (!res.ok) throw new Error('Failed to update config')
  return res.json()
}

export async function fetchClimate(): Promise<any> {
  const res = await fetch(`${BASE_URL}/research/climate`)
  if (!res.ok) throw new Error('Failed to fetch climate')
  return res.json()
}

export async function fetchFeatures(): Promise<any> {
  const res = await fetch(`${BASE_URL}/research/features`)
  if (!res.ok) throw new Error('Failed to fetch features')
  return res.json()
}

export async function fetchAlphaVectors(limit = 10): Promise<any> {
  const res = await fetch(`${BASE_URL}/research/alpha-vectors?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch alpha vectors')
  return res.json()
}

export async function triggerRlmScan(sourceType = 'forum', sourcePath?: string, keywords?: string): Promise<any> {
  const params = new URLSearchParams()
  params.set('source_type', sourceType)
  if (sourcePath) params.set('source_path', sourcePath)
  if (keywords) params.set('keywords', keywords)
  const res = await fetch(`${BASE_URL}/research/rlm-scan?${params}`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to trigger RLM scan')
  return res.json()
}

export async function fetchRiskSummary(): Promise<RiskSummary> {
  const res = await fetch(`${BASE_URL}/risk/summary`)
  if (!res.ok) throw new Error('Failed to fetch risk summary')
  return res.json()
}

export async function fetchVaR(confidence = 0.95): Promise<VaRBreakdown> {
  const res = await fetch(`${BASE_URL}/risk/var?confidence=${confidence}`)
  if (!res.ok) throw new Error('Failed to fetch VaR')
  return res.json()
}

export async function fetchCorrelation(): Promise<CorrelationData> {
  const res = await fetch(`${BASE_URL}/risk/correlation`)
  if (!res.ok) throw new Error('Failed to fetch correlation')
  return res.json()
}

export async function fetchDrawdown(): Promise<DrawdownMetrics> {
  const res = await fetch(`${BASE_URL}/risk/drawdown`)
  if (!res.ok) throw new Error('Failed to fetch drawdown')
  return res.json()
}

export async function fetchPortfolioRisk(): Promise<PortfolioRisk> {
  const res = await fetch(`${BASE_URL}/risk/portfolio`)
  if (!res.ok) throw new Error('Failed to fetch portfolio risk')
  return res.json()
}
