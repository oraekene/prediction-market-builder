import type { Market } from '@/types/market'
import type { Strategy } from '@/types/strategy'
import type { PaperWallet, PaperOrderItem, PaperPerformance } from '@/types/paperTrading'
import type { MetaStrategy, StrategyScore } from '@/types/meta_strategy'

interface ResearchSession {
  id: string
  mode: string
  status: string
  current_iteration: number
  avg_sharpe: number
  created_at: string
}
import type { RiskSummary, CorrelationPair, DrawdownMetrics } from '@/types/risk'
import type { SafeWallet } from '@/types/withdrawal'

export function createMockMarket(overrides?: Partial<Market>): Market {
  return {
    id: 'market-1',
    question: 'Will BTC exceed $100k by Dec 2026?',
    platform: 'polymarket',
    status: 'active',
    closing_date: '2026-12-31T23:59:59Z',
    volume: 1_500_000,
    probability: 0.65,
    ...overrides,
  }
}

export function createMockMarkets(count = 3): Market[] {
  return Array.from({ length: count }, (_, i) =>
    createMockMarket({
      id: `market-${i + 1}`,
      question: `Market question ${i + 1}`,
      volume: (i + 1) * 500_000,
      probability: 0.5 + i * 0.1,
    }),
  )
}

export function createMockStrategy(overrides?: Partial<Strategy>): Strategy {
  return {
    id: 'strategy-1',
    name: 'Test Strategy',
    description: 'A test strategy',
    status: 'active',
    mode: 'paper',
    nodes: [],
    edges: [],
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

export function createMockStrategies(count = 3): Strategy[] {
  return Array.from({ length: count }, (_, i) =>
    createMockStrategy({
      id: `strategy-${i + 1}`,
      name: `Strategy ${i + 1}`,
      status: i === 0 ? 'active' : 'paused',
    }),
  )
}

export function createMockResearchSession(overrides?: Partial<ResearchSession>): ResearchSession {
  return {
    id: `sess-${overrides?.id ?? '1'}`,
    mode: 'manual',
    status: 'completed',
    current_iteration: 5,
    avg_sharpe: 1.5,
    created_at: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

export function createMockPaperWallet(overrides?: Partial<PaperWallet>): PaperWallet {
  return {
    id: 'wallet-1',
    cash_balance: 10000,
    total_value: 12500,
    market_value: 2500,
    pnl: 2500,
    pnl_percent: 0.25,
    position_count: 3,
    ...overrides,
  }
}

export function createMockPaperOrder(overrides?: Partial<PaperOrderItem>): PaperOrderItem {
  return {
    id: 'order-1',
    market_id: 'market-1',
    platform: 'polymarket',
    side: 'buy',
    price: 0.65,
    amount: 100,
    filled_price: 0.65,
    status: 'filled',
    created_at: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

export function createMockPaperPerformance(overrides?: Partial<PaperPerformance>): PaperPerformance {
  return {
    total_trades: 25,
    win_rate: 0.6,
    sharpe: 1.8,
    sortino: 2.2,
    max_drawdown: 0.12,
    profit_factor: 1.5,
    avg_return: 0.03,
    total_pnl: 2500,
    ...overrides,
  }
}

export function createMockMetaStrategy(overrides?: Partial<MetaStrategy>): MetaStrategy {
  return {
    id: 'meta-1',
    name: 'Test Meta Strategy',
    description: 'A test meta-strategy',
    mode: 'rankings',
    status: 'active',
    pool_size: 5,
    winner: null,
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

export function createMockStrategyScore(overrides?: Partial<StrategyScore>): StrategyScore {
  return {
    id: 'score-1',
    strategy_id: 'strategy-1',
    strategy_name: 'Strategy 1',
    rank: 1,
    composite_score: 0.85,
    win_rate: 0.6,
    sharpe: 1.5,
    total_pnl: 1500,
    is_winner: true,
    ...overrides,
  }
}

export function createMockRiskSummary(overrides?: Partial<RiskSummary>): RiskSummary {
  return {
    current_drawdown: 0.05,
    max_drawdown: 0.15,
    var_95: 0.02,
    var_99: 0.04,
    correlation_count: 10,
    position_count: 5,
    ...overrides,
  }
}

export function createMockCorrelationPair(overrides?: Partial<CorrelationPair>): CorrelationPair {
  return {
    id1: 'market-1',
    id2: 'market-2',
    label1: 'Market 1',
    label2: 'Market 2',
    correlation: 0.65,
    ...overrides,
  }
}

export function createMockDrawdown(overrides?: Partial<DrawdownMetrics>): DrawdownMetrics {
  return {
    current_drawdown: 0.05,
    max_drawdown: 0.15,
    peak_capital: 15000,
    current_capital: 14250,
    ...overrides,
  }
}

export function createMockSafeWallet(overrides?: Partial<SafeWallet>): SafeWallet {
  return {
    id: 'safe-1',
    name: 'Test Safe Wallet',
    balance: 50000,
    protected_amount: 30000,
    status: 'active',
    created_at: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

export const mockStats = {
  total_sessions: 42,
  total_kept: 15,
  avg_sharpe: 1.25,
  keep_rate: 0.36,
  best_sharpe: 2.85,
}

export const mockEmptyStats = {
  total_sessions: 0,
  total_kept: 0,
  avg_sharpe: 0,
  keep_rate: 0,
  best_sharpe: 0,
}
