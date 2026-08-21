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
    platform: 'polymarket',
    platform_market_id: 'market-1',
    title: 'Will BTC exceed $100k by Dec 2026?',
    status: 'open',
    current_odds: 0.65,
    volume: 1_500_000,
    liquidity: 800_000,
    participants: 1200,
    outcomes: ['Yes', 'No'],
    close_time: '2026-12-31T23:59:59Z',
    last_updated: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

export function createMockMarkets(count = 3): Market[] {
  return Array.from({ length: count }, (_, i) =>
    createMockMarket({
      id: `market-${i + 1}`,
      platform_market_id: `market-${i + 1}`,
      title: `Market question ${i + 1}`,
      volume: (i + 1) * 500_000,
      current_odds: 0.5 + i * 0.1,
    }),
  )
}

export function createMockStrategy(overrides?: Partial<Strategy>): Strategy {
  return {
    id: 'strategy-1',
    name: 'Test Strategy',
    description: 'A test strategy',
    status: 'active',
    mode: 'node',
    nodes: [],
    edges: [],
    risk_profile: {},
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
    user_id: 'user-1',
    initial_balance: 10000,
    current_balance: 12500,
    pnl: 2500,
    pnl_pct: 25.0,
    currency: 'USD',
    is_active: true,
    open_positions: [],
    recent_trades: [],
    ...overrides,
  }
}

export function createMockPaperOrder(overrides?: Partial<PaperOrderItem>): PaperOrderItem {
  return {
    id: 'order-1',
    market_id: 'market-1',
    market_title: 'Test market',
    platform: 'polymarket',
    side: 'buy',
    amount: 100,
    filled_amount: 100,
    price: 0.65,
    fill_price: 0.65,
    pnl: null,
    slippage: null,
    status: 'filled',
    created_at: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

export function createMockPaperPerformance(overrides?: Partial<PaperPerformance>): PaperPerformance {
  return {
    total_trades: 25,
    winning_trades: 15,
    losing_trades: 10,
    win_rate: 0.6,
    total_pnl: 2500,
    sharpe_ratio: 1.8,
    max_drawdown: 0.12,
    avg_return: 0.03,
    avg_rr: 1.5,
    kelly_optimal: 0.25,
    edge: 0.05,
    profit_factor: 1.5,
    calibration: null,
    regime_buckets: {},
    current_balance: 12500,
    initial_balance: 10000,
    ...overrides,
  }
}

export function createMockMetaStrategy(overrides?: Partial<MetaStrategy>): MetaStrategy {
  return {
    id: 'meta-1',
    user_id: 'user-1',
    name: 'Test Meta Strategy',
    description: 'A test meta-strategy',
    mode: 'competition',
    status: 'active',
    strategy_ids: [],
    scoring_config: {
      metrics: {
        sharpe: 0.2, win_rate: 0.15, profit_factor: 0.15, max_drawdown: 0.1,
        confidence: 0.1, expected_value: 0.1, signal_strength: 0.1, consistency: 0.1,
      },
    },
    promotion_config: { interval: 'daily', interval_days: null, probation_hours: 48, evaluation_window_days: 30 },
    confluence_config: { threshold: 3, source: 'top_n', from_top: 5, manual_strategy_ids: [] },
    current_winner_id: undefined,
    last_promotion_at: undefined,
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

export function createMockStrategyScore(overrides?: Partial<StrategyScore>): StrategyScore {
  return {
    id: 'score-1',
    name: 'Strategy 1',
    rank: 1,
    score: 0.85,
    total_trades: 25,
    total_pnl: 1500,
    win_rate: 0.6,
    confidence: 0,
    expected_value: 0,
    signal_strength: 0,
    consistency: 0,
    is_winner: true,
    ...overrides,
  }
}

export function createMockRiskSummary(overrides?: Partial<RiskSummary>): RiskSummary {
  return {
    var_95: 0.02,
    es_95: 0.04,
    max_drawdown: 0.15,
    current_drawdown: 0.05,
    concentration: 0.3,
    portfolio_volatility: 0.12,
    ...overrides,
  }
}

export function createMockCorrelationPair(overrides?: Partial<CorrelationPair>): CorrelationPair {
  return {
    asset_a: 'market-1',
    asset_b: 'market-2',
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
    user_id: 'user-1',
    name: 'Test Safe Wallet',
    currency: 'USDC',
    balance: 50000,
    address: null,
    is_disconnected: true,
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-15T10:00:00Z',
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
