export type MetaStrategyMode = 'standard' | 'competition' | 'confluence' | 'both'
export type MetaStrategyConsumer = 'paper_trading' | 'live' | 'backtesting' | 'copy_trading'

export interface ScoringConfig {
  metrics: {
    sharpe: number
    win_rate: number
    profit_factor: number
    max_drawdown: number
  }
  evaluation_window_days: number
}

export interface PromotionConfig {
  interval: 'daily' | 'weekly' | 'monthly' | 'custom'
  interval_days?: number | null
  probation_hours: number
}

export interface ConfluenceConfig {
  threshold: number
  source: 'top_n' | 'manual'
  from_top: number
  manual_strategy_ids: string[]
}

export interface MetaStrategy {
  id: string
  user_id: string
  name: string
  description?: string
  mode: MetaStrategyMode
  status: string
  strategy_ids: string[]
  scoring_config: ScoringConfig
  promotion_config: PromotionConfig
  confluence_config: ConfluenceConfig
  consumer?: MetaStrategyConsumer
  current_winner_id?: string
  last_promotion_at?: string
  created_at: string
  updated_at: string
}

export interface StrategyScore {
  id: string
  name: string
  rank: number
  score: number
  total_trades: number
  total_pnl: number
  win_rate: number
  is_winner: boolean
}

export interface RankingsResponse {
  meta_strategy_id: string
  name: string
  mode: string
  current_winner_id?: string
  last_promotion_at?: string
  rankings: StrategyScore[]
}

export interface StrategyPerformance {
  id: string
  name: string
  pnl: number
  trades: number
  win_rate: number
}

export interface PerformanceResponse {
  meta_strategy_id: string
  name: string
  mode: string
  current_winner_id?: string
  total_pnl: number
  total_trades: number
  overall_win_rate: number
  strategy_performances: StrategyPerformance[]
}

export interface CreateMetaStrategyRequest {
  user_id?: string
  name: string
  description?: string
  mode?: MetaStrategyMode
  strategy_ids?: string[]
  scoring_config?: ScoringConfig
  promotion_config?: PromotionConfig
  confluence_config?: ConfluenceConfig
  consumer?: MetaStrategyConsumer
}

export interface UpdateMetaStrategyRequest {
  name?: string
  description?: string
  mode?: MetaStrategyMode
  status?: string
  strategy_ids?: string[]
  scoring_config?: ScoringConfig
  promotion_config?: PromotionConfig
  confluence_config?: ConfluenceConfig
  consumer?: MetaStrategyConsumer | null
  current_winner_id?: string | null
}

export const DEFAULT_SCORING_CONFIG: ScoringConfig = {
  metrics: { sharpe: 0.35, win_rate: 0.25, profit_factor: 0.25, max_drawdown: 0.15 },
  evaluation_window_days: 30,
}

export const DEFAULT_PROMOTION_CONFIG: PromotionConfig = {
  interval: 'daily',
  interval_days: null,
  probation_hours: 48,
}

export const DEFAULT_CONFLUENCE_CONFIG: ConfluenceConfig = {
  threshold: 3,
  source: 'top_n',
  from_top: 5,
  manual_strategy_ids: [],
}
