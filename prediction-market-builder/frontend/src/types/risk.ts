export interface RiskSummary {
  var_95: number
  es_95: number
  max_drawdown: number
  current_drawdown: number
  concentration: number
  portfolio_volatility: number
}

export interface VaRBreakdown {
  historical: number
  parametric: number
  tabpfn: number | null
  confidence: number
}

export interface CorrelationPair {
  asset_a: string
  asset_b: string
  correlation: number
}

export interface CorrelationData {
  pairs: CorrelationPair[]
  total_assets: number
}

export interface DrawdownMetrics {
  current_drawdown: number
  peak_capital: number
  current_capital: number
  max_drawdown: number
}

export interface PositionRisk {
  market_id: string
  size: number
  var_contribution: number
  concentration_pct: number
}

export interface PortfolioRisk {
  positions: PositionRisk[]
}
