import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  fetchMarkets, fetchMarket, fetchStrategies, createStrategy, fetchStrategy,
  updateStrategy, deleteStrategy, fetchPortfolio, fetchAnalyticsSummary,
  fetchAnalyticsBacktests, triggerResearchRun, triggerContinuousResearch,
  stopResearch, fetchResearchSessions, fetchResearchSession, fetchResearchResults,
  fetchResearchStats, fetchResearchConfig, updateResearchConfig, fetchClimate,
  fetchFeatures, fetchAlphaVectors, triggerRlmScan, fetchRiskSummary,
  fetchVaR, fetchCorrelation, fetchDrawdown, fetchPortfolioRisk,
  fetchMetaStrategies, createMetaStrategy, fetchMetaStrategy,
  updateMetaStrategy, deleteMetaStrategy, addStrategyToMetaPool,
  removeStrategyFromMetaPool, fetchMetaRankings, evaluateMetaPromotion,
  forceMetaPromote, fetchMetaPerformance, fetchShapExplanation,
  fetchShapSessionAggregate, explainFeatures,
} from './api'

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

describe('fetchMarkets', () => {
  it('calls GET /api/markets with params', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ markets: [], total: 0 }))
    await fetchMarkets({ category: 'crypto' })
    expect(mockApiFetch).toHaveBeenCalledWith('/api/markets?category=crypto')
  })

  it('throws on error', async () => {
    mockApiFetch.mockResolvedValue(mockResponse(null, false))
    await expect(fetchMarkets()).rejects.toThrow('Failed to fetch markets')
  })
})

describe('fetchMarket', () => {
  it('calls GET /api/markets/:id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ id: 'm1' }))
    const result = await fetchMarket('m1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/markets/m1')
    expect(result).toEqual({ id: 'm1' })
  })
})

describe('fetchStrategies', () => {
  it('calls GET /api/strategies', async () => {
    mockApiFetch.mockResolvedValue(mockResponse([]))
    await fetchStrategies()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/strategies')
  })
})

describe('createStrategy', () => {
  it('calls POST /api/strategies with body', async () => {
    const data = { name: 'test' }
    mockApiFetch.mockResolvedValue(mockResponse({ id: 's1' }))
    const result = await createStrategy(data)
    expect(mockApiFetch).toHaveBeenCalledWith('/api/strategies', {
      method: 'POST', body: JSON.stringify(data),
    })
    expect(result).toEqual({ id: 's1' })
  })
})

describe('fetchStrategy', () => {
  it('calls GET /api/strategies/:id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ id: 's1' }))
    await fetchStrategy('s1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/strategies/s1')
  })
})

describe('updateStrategy', () => {
  it('calls PUT /api/strategies/:id', async () => {
    const data = { name: 'updated' }
    mockApiFetch.mockResolvedValue(mockResponse({ id: 's1' }))
    await updateStrategy('s1', data)
    expect(mockApiFetch).toHaveBeenCalledWith('/api/strategies/s1', {
      method: 'PUT', body: JSON.stringify(data),
    })
  })
})

describe('deleteStrategy', () => {
  it('calls DELETE /api/strategies/:id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await deleteStrategy('s1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/strategies/s1', {
      method: 'DELETE',
    })
  })
})

describe('fetchPortfolio', () => {
  it('calls GET /api/portfolio', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchPortfolio()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/portfolio')
  })
})

describe('fetchAnalyticsSummary', () => {
  it('calls GET /api/analytics/summary', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchAnalyticsSummary()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/analytics/summary')
  })
})

describe('fetchAnalyticsBacktests', () => {
  it('calls GET /api/analytics/backtests', async () => {
    mockApiFetch.mockResolvedValue(mockResponse([]))
    await fetchAnalyticsBacktests()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/analytics/backtests')
  })
})

describe('triggerResearchRun', () => {
  it('calls POST /api/research/run with params', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await triggerResearchRun('s1', 'sharpe_max')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/research/run?strategy_id=s1&preset=sharpe_max',
      { method: 'POST' },
    )
  })

  it('works without strategyId', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await triggerResearchRun()
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/research/run?preset=sharpe_max',
      { method: 'POST' },
    )
  })
})

describe('triggerContinuousResearch', () => {
  it('calls POST /api/research/run-continuous', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await triggerContinuousResearch()
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/research/run-continuous?preset=sharpe_max',
      { method: 'POST' },
    )
  })
})

describe('stopResearch', () => {
  it('calls POST /api/research/stop', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await stopResearch('sess-1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/research/stop?session_id=sess-1',
      { method: 'POST' },
    )
  })
})

describe('fetchResearchSessions', () => {
  it('calls GET /api/research/sessions', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ sessions: [], total: 0 }))
    const result = await fetchResearchSessions()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/research/sessions')
    expect(result).toEqual({ sessions: [], total: 0 })
  })
})

describe('fetchResearchSession', () => {
  it('calls GET /api/research/sessions/:id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchResearchSession('sess-1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/research/sessions/sess-1')
  })
})

describe('fetchResearchResults', () => {
  it('calls GET with session ID and limit', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ results: [], total: 0 }))
    await fetchResearchResults('sess-1', 100)
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/research/sessions/sess-1/results?limit=100',
    )
  })

  it('defaults limit to 50', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ results: [], total: 0 }))
    await fetchResearchResults('sess-1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/research/sessions/sess-1/results?limit=50',
    )
  })
})

describe('fetchResearchStats', () => {
  it('calls GET /api/research/stats', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchResearchStats()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/research/stats')
  })
})

describe('fetchResearchConfig', () => {
  it('calls GET /api/research/config', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchResearchConfig()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/research/config')
  })
})

describe('updateResearchConfig', () => {
  it('calls PUT /api/research/config with query params', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await updateResearchConfig({ max_iterations: '100' })
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/research/config?max_iterations=100',
      { method: 'PUT' },
    )
  })
})

describe('fetchClimate', () => {
  it('calls GET /api/research/climate', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchClimate()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/research/climate')
  })
})

describe('fetchFeatures', () => {
  it('calls GET /api/research/features', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchFeatures()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/research/features')
  })
})

describe('fetchAlphaVectors', () => {
  it('calls GET /api/research/alpha-vectors with limit', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({ vectors: [] }))
    await fetchAlphaVectors(5)
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/research/alpha-vectors?limit=5',
    )
  })
})

describe('triggerRlmScan', () => {
  it('calls POST /api/research/rlm-scan with params', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await triggerRlmScan('forum', '/r/politics', 'election')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/research/rlm-scan?source_type=forum&source_path=%2Fr%2Fpolitics&keywords=election',
      { method: 'POST' },
    )
  })
})

describe('fetchRiskSummary', () => {
  it('calls GET /api/risk/summary', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchRiskSummary()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/risk/summary')
  })
})

describe('fetchVaR', () => {
  it('calls GET /api/risk/var with confidence', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchVaR(0.99)
    expect(mockApiFetch).toHaveBeenCalledWith('/api/risk/var?confidence=0.99')
  })
})

describe('fetchCorrelation', () => {
  it('calls GET /api/risk/correlation', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchCorrelation()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/risk/correlation')
  })
})

describe('fetchDrawdown', () => {
  it('calls GET /api/risk/drawdown', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchDrawdown()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/risk/drawdown')
  })
})

describe('fetchPortfolioRisk', () => {
  it('calls GET /api/risk/portfolio', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchPortfolioRisk()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/risk/portfolio')
  })
})

describe('fetchMetaStrategies', () => {
  it('calls GET /api/meta-strategies with params', async () => {
    mockApiFetch.mockResolvedValue(mockResponse([]))
    await fetchMetaStrategies({ status: 'active' })
    expect(mockApiFetch).toHaveBeenCalledWith('/api/meta-strategies?status=active')
  })
})

describe('createMetaStrategy', () => {
  it('calls POST /api/meta-strategies', async () => {
    const data = { name: 'test' }
    mockApiFetch.mockResolvedValue(mockResponse({ id: 'ms1' }))
    const result = await createMetaStrategy(data)
    expect(mockApiFetch).toHaveBeenCalledWith('/api/meta-strategies', {
      method: 'POST', body: JSON.stringify(data),
    })
    expect(result).toEqual({ id: 'ms1' })
  })
})

describe('fetchMetaStrategy', () => {
  it('calls GET /api/meta-strategies/:id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchMetaStrategy('ms1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/meta-strategies/ms1')
  })
})

describe('updateMetaStrategy', () => {
  it('calls PUT /api/meta-strategies/:id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await updateMetaStrategy('ms1', { name: 'new' })
    expect(mockApiFetch).toHaveBeenCalledWith('/api/meta-strategies/ms1', {
      method: 'PUT', body: JSON.stringify({ name: 'new' }),
    })
  })
})

describe('deleteMetaStrategy', () => {
  it('calls DELETE /api/meta-strategies/:id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await deleteMetaStrategy('ms1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/meta-strategies/ms1', {
      method: 'DELETE',
    })
  })
})

describe('addStrategyToMetaPool', () => {
  it('calls POST with strategy_id param', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await addStrategyToMetaPool('ms1', 's1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/meta-strategies/ms1/strategies?strategy_id=s1',
      { method: 'POST' },
    )
  })
})

describe('removeStrategyFromMetaPool', () => {
  it('calls DELETE with strategy ID in path', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await removeStrategyFromMetaPool('ms1', 's1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/meta-strategies/ms1/strategies/s1',
      { method: 'DELETE' },
    )
  })
})

describe('fetchMetaRankings', () => {
  it('calls GET /api/meta-strategies/:id/rankings', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchMetaRankings('ms1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/meta-strategies/ms1/rankings')
  })
})

describe('evaluateMetaPromotion', () => {
  it('calls POST /api/meta-strategies/:id/evaluate', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await evaluateMetaPromotion('ms1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/meta-strategies/ms1/evaluate',
      { method: 'POST' },
    )
  })
})

describe('forceMetaPromote', () => {
  it('calls POST with strategy_id', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await forceMetaPromote('ms1', 's1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/meta-strategies/ms1/force-promote?strategy_id=s1',
      { method: 'POST' },
    )
  })
})

describe('fetchMetaPerformance', () => {
  it('calls GET /api/meta-strategies/:id/performance', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchMetaPerformance('ms1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/meta-strategies/ms1/performance')
  })
})

describe('fetchShapExplanation', () => {
  it('calls GET /api/explainability/:resultId', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchShapExplanation('res-1')
    expect(mockApiFetch).toHaveBeenCalledWith('/api/explainability/res-1')
  })
})

describe('fetchShapSessionAggregate', () => {
  it('calls GET /api/explainability/session/:id/aggregate', async () => {
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await fetchShapSessionAggregate('sess-1')
    expect(mockApiFetch).toHaveBeenCalledWith(
      '/api/explainability/session/sess-1/aggregate',
    )
  })
})

describe('explainFeatures', () => {
  it('calls POST /api/explainability/explain', async () => {
    const features = { feature_a: 0.5 }
    mockApiFetch.mockResolvedValue(mockResponse({}))
    await explainFeatures(features, [1, 2, 3])
    expect(mockApiFetch).toHaveBeenCalledWith('/api/explainability/explain', {
      method: 'POST',
      body: JSON.stringify({ features, regime_vector: [1, 2, 3] }),
    })
  })
})
