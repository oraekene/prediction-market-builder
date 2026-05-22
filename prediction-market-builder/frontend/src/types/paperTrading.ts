export interface PaperWallet {
  id: string
  user_id: string
  initial_balance: number
  current_balance: number
  pnl: number
  pnl_pct: number
  currency: string
  is_active: boolean
  open_positions: PaperOrderItem[]
  recent_trades: PaperOrderItem[]
}

export interface PaperOrderItem {
  id: string
  market_id: string
  market_title: string
  platform: string
  side: string
  amount: number
  filled_amount: number
  price: number
  fill_price: number | null
  pnl: number | null
  slippage: number | null
  status: 'pending' | 'partial' | 'filled' | 'cancelled'
  created_at: string | null
}

export interface PaperOrderRequest {
  wallet_id: string
  platform?: string
  market_id: string
  market_title?: string
  side: string
  amount: number
  price: number
  strategy_id?: string
  risk_profile?: Record<string, unknown>
}

export interface PaperOrderResponse {
  success: boolean
  order?: PaperOrderItem
  wallet_balance?: number
  slippage?: number
  fill_probability?: number
  error?: string
  violations?: string[]
}

export interface PaperPerformance {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  sharpe_ratio: number
  max_drawdown: number
  avg_return: number
  avg_rr: number
  kelly_optimal: number
  edge: number
  profit_factor: number
  calibration: number | null
  regime_buckets: Record<string, unknown>
  current_balance: number | null
  initial_balance: number | null
}

export interface PerformanceMetricResponse {
  metric: string
  value: number | null
  window: number
  total_available: number
}

export interface StrategyComparison {
  comparisons: PaperPerformance[]
}
