export interface NodeTypeDefinition {
  label: string
  backendType: string
  category: string
  color: string
  defaultConfig: Record<string, unknown>
  description: string
}

export const NODE_TYPE_REGISTRY: Record<string, NodeTypeDefinition> = {
  // Sources
  'Polymarket': { label: 'Polymarket', backendType: 'polymarket_source', category: 'Sources', color: '#22c55e', defaultConfig: {}, description: 'Fetch markets from Polymarket' },
  'Kalshi': { label: 'Kalshi', backendType: 'kalshi_source', category: 'Sources', color: '#22c55e', defaultConfig: {}, description: 'Fetch markets from Kalshi' },
  'Drift': { label: 'Drift', backendType: 'drift_source', category: 'Sources', color: '#22c55e', defaultConfig: {}, description: 'Fetch markets from Drift' },
  'Web Search': { label: 'Web Search', backendType: 'web_search', category: 'Sources', color: '#22c55e', defaultConfig: {}, description: 'Search the web for information' },
  'News': { label: 'News', backendType: 'news_source', category: 'Sources', color: '#22c55e', defaultConfig: {}, description: 'Search news articles' },

  // Filters
  'TabPFN Signal': { label: 'TabPFN Signal', backendType: 'tabpfn_signal', category: 'Filters', color: '#3b82f6', defaultConfig: {}, description: 'ML signal validation via TabPFN' },
  'Toto-2 Climate': { label: 'Toto-2 Climate', backendType: 'toto2_climate', category: 'Filters', color: '#3b82f6', defaultConfig: {}, description: 'Market regime/climate assessment' },
  'Sentiment': { label: 'Sentiment', backendType: 'sentiment_filter', category: 'Filters', color: '#3b82f6', defaultConfig: {}, description: 'Text sentiment analysis' },
  'SHAP Feature Importance': { label: 'SHAP Feature Importance', backendType: 'shap_feature_importance', category: 'Filters', color: '#3b82f6', defaultConfig: { min_importance: 0.0, top_k: 5 }, description: 'SHAP feature importance ranking' },

  // Conditions
  'Threshold': { label: 'Threshold', backendType: 'threshold_condition', category: 'Conditions', color: '#eab308', defaultConfig: { field: 'current_odds', operator: 'lt', threshold: 0.5 }, description: 'Check if a field meets a threshold' },
  'Time-Based': { label: 'Time-Based', backendType: 'time_condition', category: 'Conditions', color: '#eab308', defaultConfig: { operator: 'after' }, description: 'Time-based condition' },
  'AND/OR': { label: 'AND/OR', backendType: 'and_or_gate', category: 'Conditions', color: '#eab308', defaultConfig: { gate_type: 'and' }, description: 'Logic gate for combining conditions' },
  'Branch': { label: 'Branch', backendType: 'branch', category: 'Conditions', color: '#eab308', defaultConfig: { branch_if: true }, description: 'Branch based on condition result' },

  // Actions
  'Place Bet': { label: 'Place Bet', backendType: 'place_bet', category: 'Actions', color: '#f97316', defaultConfig: {}, description: 'Place a bet order' },
  'Send Alert': { label: 'Send Alert', backendType: 'alert_action', category: 'Actions', color: '#f97316', defaultConfig: { message: 'Risk threshold breached', severity: 'warning' }, description: 'Send an alert notification' },
  'Forward': { label: 'Forward', backendType: 'forward', category: 'Actions', color: '#f97316', defaultConfig: {}, description: 'Forward data downstream' },
  'Webhook': { label: 'Webhook', backendType: 'webhook', category: 'Actions', color: '#f97316', defaultConfig: {}, description: 'POST to external webhook' },
  'Close Position': { label: 'Close Position', backendType: 'close_position', category: 'Actions', color: '#f97316', defaultConfig: { close_pct: 100 }, description: 'Close an open position' },
  'Convert to Stablecoin': { label: 'Convert to Stablecoin', backendType: 'convert_to_stablecoin', category: 'Actions', color: '#f97316', defaultConfig: { target_stablecoin: 'USDC', convert_pct: 100 }, description: 'Convert profits to stablecoin' },

  // Risk - Position Exits
  'Stop-Loss': { label: 'Stop-Loss', backendType: 'stop_loss', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { stop_loss: 0.1 }, description: 'Exit on loss from entry price' },
  'Take Profit': { label: 'Take Profit', backendType: 'take_profit', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { take_profit: 0.2 }, description: 'Exit on gain from entry price' },
  'Trailing Stop': { label: 'Trailing Stop', backendType: 'trailing_stop', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { trail_pct: 0.05 }, description: 'Exit when price falls X% from peak' },
  'Tightening Trailing Stop': { label: 'Tightening Trailing Stop', backendType: 'tightening_trailing_stop', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { thresholds: [[0.05, 0.03], [0.10, 0.02], [0.20, 0.01]] }, description: 'Trail that tightens as profit grows' },
  'ATR Stop': { label: 'ATR Stop', backendType: 'atr_stop', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { atr_multiplier: 2.0, atr_period: 14 }, description: 'ATR-based adaptive stop loss' },
  'Volatility Stop': { label: 'Volatility Stop', backendType: 'volatility_stop', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { vol_threshold: 0.03 }, description: 'Exit when volatility exceeds threshold' },
  'Break-Even Stop': { label: 'Break-Even Stop', backendType: 'break_even_stop', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { trigger_pct: 0.02, buffer_pct: 0.005 }, description: 'Move stop to entry after profit' },
  'Time Exit': { label: 'Time Exit', backendType: 'time_exit', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { max_hold_days: 30 }, description: 'Exit after max hold duration' },
  'Scaling Exit': { label: 'Scaling Exit', backendType: 'scaling_exit', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { tiers: [{ profit_pct: 0.10, exit_pct: 33 }, { profit_pct: 0.25, exit_pct: 50 }] }, description: 'Partial exits at profit tiers' },
  'Moving Average Exit': { label: 'Moving Average Exit', backendType: 'moving_average_exit', category: 'Risk - Position Exits', color: '#ef4444', defaultConfig: { period: 20, ma_type: 'sma' }, description: 'Exit on MA crossover' },

  // Risk - Portfolio Limits
  'Drawdown': { label: 'Drawdown', backendType: 'drawdown_monitor', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_drawdown: 0.15 }, description: 'Monitor portfolio drawdown' },
  'VaR Check': { label: 'VaR Check', backendType: 'var_check', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { confidence: 0.95, limit: 0.05 }, description: 'Value at Risk check' },
  'Expected Shortfall': { label: 'Expected Shortfall', backendType: 'expected_shortfall_check', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { confidence: 0.95, limit: 0.08 }, description: 'CVaR / Expected Shortfall check' },
  'Daily Loss Limit': { label: 'Daily Loss Limit', backendType: 'daily_loss_limit', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_daily_loss: 0.03 }, description: 'Halt on daily loss exceed' },
  'Weekly Loss Limit': { label: 'Weekly Loss Limit', backendType: 'weekly_loss_limit', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_weekly_loss: 0.05 }, description: 'Halt on weekly loss exceed' },
  'Monthly Loss Limit': { label: 'Monthly Loss Limit', backendType: 'monthly_loss_limit', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_monthly_loss: 0.10 }, description: 'Halt on monthly loss exceed' },
  'Max Position Count': { label: 'Max Position Count', backendType: 'max_position_count', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_count: 10 }, description: 'Limit number of open positions' },
  'Max Gross Exposure': { label: 'Max Gross Exposure', backendType: 'max_gross_exposure', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_exposure: 1.0 }, description: 'Limit total notional exposure' },
  'Max Net Exposure': { label: 'Max Net Exposure', backendType: 'max_net_exposure', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_net_exposure: 0.5 }, description: 'Limit net directional exposure' },
  'Leverage Limit': { label: 'Leverage Limit', backendType: 'leverage_limit', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_leverage: 2.0 }, description: 'Limit portfolio leverage' },
  'Sector Exposure Limit': { label: 'Sector Exposure Limit', backendType: 'sector_exposure_limit', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { sector_limits: {} }, description: 'Limit per-sector exposure' },
  'Beta Exposure Limit': { label: 'Beta Exposure Limit', backendType: 'beta_exposure_limit', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_beta: 1.0 }, description: 'Limit portfolio beta' },
  'Volatility Targeting': { label: 'Volatility Targeting', backendType: 'volatility_targeting', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { target_vol: 0.10 }, description: 'Scale positions to target volatility' },
  'Stress Test': { label: 'Stress Test', backendType: 'stress_test', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { scenarios: [] }, description: 'Test portfolio under stress scenarios' },
  'Monte Carlo Risk': { label: 'Monte Carlo Risk', backendType: 'monte_carlo_risk', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { num_simulations: 1000, confidence: 0.95 }, description: 'Monte Carlo VaR simulation' },
  'Tail Risk Check': { label: 'Tail Risk Check', backendType: 'tail_risk_check', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { max_kurtosis: 5.0, max_skewness: -0.5 }, description: 'Monitor return distribution tails' },
  'Liquidity Risk': { label: 'Liquidity Risk', backendType: 'liquidity_risk_check', category: 'Risk - Portfolio Limits', color: '#ef4444', defaultConfig: { min_liquidity: 10000, max_spread_pct: 0.05 }, description: 'Check market liquidity' },

  // Risk - Diversification
  'Correlation Check': { label: 'Correlation Check', backendType: 'correlation_check', category: 'Risk - Diversification', color: '#ef4444', defaultConfig: { max_correlation: 0.7 }, description: 'Check cross-position correlation' },
  'Concentration Check': { label: 'Concentration Check', backendType: 'concentration_check', category: 'Risk - Diversification', color: '#ef4444', defaultConfig: { max_concentration: 0.3 }, description: 'Check position concentration' },
  'Factor Exposure': { label: 'Factor Exposure', backendType: 'factor_exposure_check', category: 'Risk - Diversification', color: '#ef4444', defaultConfig: { max_factor_exposures: {} }, description: 'Check factor exposures' },
  'MCR Check': { label: 'MCR Check', backendType: 'mcr_check', category: 'Risk - Diversification', color: '#ef4444', defaultConfig: { max_mcr: 0.1 }, description: 'Marginal Contribution to Risk' },
  'Worst Case Portfolio': { label: 'Worst Case Portfolio', backendType: 'worst_case_portfolio', category: 'Risk - Diversification', color: '#ef4444', defaultConfig: { max_worst_case_loss: 0.20 }, description: 'Worst-case loss scenario' },

  // Risk - Greeks
  'Delta Exposure': { label: 'Delta Exposure', backendType: 'delta_exposure', category: 'Risk - Greeks', color: '#ef4444', defaultConfig: { max_delta: 1.0 }, description: 'Monitor portfolio delta' },
  'Gamma Exposure': { label: 'Gamma Exposure', backendType: 'gamma_exposure', category: 'Risk - Greeks', color: '#ef4444', defaultConfig: { max_gamma: 0.5 }, description: 'Monitor portfolio gamma' },
  'Vega Exposure': { label: 'Vega Exposure', backendType: 'vega_exposure', category: 'Risk - Greeks', color: '#ef4444', defaultConfig: { max_vega: 0.5 }, description: 'Monitor portfolio vega' },
  'Theta Decay': { label: 'Theta Decay', backendType: 'theta_decay', category: 'Risk - Greeks', color: '#ef4444', defaultConfig: { max_theta_loss: 100 }, description: 'Monitor theta decay' },
  'Vanna Exposure': { label: 'Vanna Exposure', backendType: 'vanna_exposure', category: 'Risk - Greeks', color: '#ef4444', defaultConfig: { max_vanna: 0.3 }, description: 'Monitor vanna (delta sensitivity to vol)' },
  'Volga Exposure': { label: 'Volga Exposure', backendType: 'volga_exposure', category: 'Risk - Greeks', color: '#ef4444', defaultConfig: { max_volga: 0.3 }, description: 'Monitor volga (vega sensitivity to vol)' },

  // Risk - Execution
  'Circuit Breaker': { label: 'Circuit Breaker', backendType: 'circuit_breaker', category: 'Risk - Execution', color: '#ef4444', defaultConfig: { max_daily_loss: 0.05, max_consecutive_losses: 5, cooldown_seconds: 300 }, description: 'Auto-halt on extreme conditions' },
  'Slippage Guard': { label: 'Slippage Guard', backendType: 'slippage_guard', category: 'Risk - Execution', color: '#ef4444', defaultConfig: { max_slippage_pct: 0.02 }, description: 'Reject trades with high slippage' },
  'Max Consecutive Losses': { label: 'Max Consecutive Losses', backendType: 'max_consecutive_losses', category: 'Risk - Execution', color: '#ef4444', defaultConfig: { max_streak: 5 }, description: 'Halt after N consecutive losses' },
  'Cooldown Period': { label: 'Cooldown Period', backendType: 'cooldown_period', category: 'Risk - Execution', color: '#ef4444', defaultConfig: { cooldown_trades: 3 }, description: 'Pause after losing streak' },
  'Position Timeout': { label: 'Position Timeout', backendType: 'position_timeout', category: 'Risk - Execution', color: '#ef4444', defaultConfig: { max_hold_seconds: 86400 }, description: 'Force-close after max hold time' },

  // Risk - Regime
  'Volatility Regime': { label: 'Volatility Regime', backendType: 'volatility_regime_check', category: 'Risk - Regime', color: '#ef4444', defaultConfig: { target_regime: 'normal' }, description: 'Check volatility regime' },
  'Correlation Regime Shift': { label: 'Correlation Regime Shift', backendType: 'correlation_regime_shift', category: 'Risk - Regime', color: '#ef4444', defaultConfig: { correlation_spike_threshold: 0.3 }, description: 'Detect correlation regime changes' },
  'Toxicity Detection': { label: 'Toxicity Detection', backendType: 'toxicity_detection', category: 'Risk - Regime', color: '#ef4444', defaultConfig: { vpin_threshold: 0.7 }, description: 'Detect toxic order flow (VPIN)' },
  'Order Flow Imbalance': { label: 'Order Flow Imbalance', backendType: 'order_flow_imbalance', category: 'Risk - Regime', color: '#ef4444', defaultConfig: { imbalance_threshold: 0.3 }, description: 'Check bid/ask order flow imbalance' },

  // Risk - Portfolio Construction
  'Kelly Criterion': { label: 'Kelly Criterion', backendType: 'position_sizer', category: 'Risk - Portfolio Construction', color: '#ef4444', defaultConfig: { method: 'kelly' }, description: 'Kelly-optimal position sizing' },
  'Risk Parity': { label: 'Risk Parity', backendType: 'risk_parity_allocation', category: 'Risk - Portfolio Construction', color: '#ef4444', defaultConfig: {}, description: 'Risk parity allocation' },
  'Mean-Variance Optimization': { label: 'Mean-Variance Optimization', backendType: 'mean_variance_optimization', category: 'Risk - Portfolio Construction', color: '#ef4444', defaultConfig: { risk_aversion: 1.0 }, description: 'Markowitz optimization' },
  'Black-Litterman': { label: 'Black-Litterman', backendType: 'black_litterman', category: 'Risk - Portfolio Construction', color: '#ef4444', defaultConfig: { views: {}, tau: 0.05 }, description: 'Black-Litterman model' },
  'Hierarchical Risk Parity': { label: 'Hierarchical Risk Parity', backendType: 'hierarchical_risk_parity', category: 'Risk - Portfolio Construction', color: '#ef4444', defaultConfig: {}, description: 'HRP allocation (De Prado)' },

  // Auto-Withdrawal
  'Withdraw to Safe Wallet': { label: 'Withdraw to Safe Wallet', backendType: 'withdraw_to_safe_wallet', category: 'Auto-Withdrawal', color: '#a855f7', defaultConfig: { withdraw_pct: 50, source: 'profits', target_currency: 'USDC' }, description: 'Transfer profits to disconnected wallet' },
  'Withdrawal Strategy': { label: 'Withdrawal Strategy', backendType: 'withdrawal_strategy', category: 'Auto-Withdrawal', color: '#a855f7', defaultConfig: { steps: [] }, description: 'Multi-step withdrawal ladder' },

  // Analysis
  'Bayesian Inference': { label: 'Bayesian Inference', backendType: 'bayesian_inference', category: 'Analysis', color: '#8b5cf6', defaultConfig: { prior: 0.5 }, description: 'Bayesian posterior calculation' },
  'Monte Carlo': { label: 'Monte Carlo', backendType: 'monte_carlo', category: 'Analysis', color: '#8b5cf6', defaultConfig: { simulations: 1000, days: 30 }, description: 'Monte Carlo simulation' },
  'Backtest': { label: 'Backtest', backendType: 'backtest', category: 'Analysis', color: '#8b5cf6', defaultConfig: {}, description: 'Backtest strategy on history' },
  'SHAP Explainability': { label: 'SHAP Explainability', backendType: 'shap_explainability', category: 'Analysis', color: '#8b5cf6', defaultConfig: {}, description: 'SHAP feature explanation' },

  // Performance (all map to the same handler with different metric slugs)
  'Current Balance': { label: 'Current Balance', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'current-balance', window: 50 }, description: 'Current wallet balance' },
  'Total P&L': { label: 'Total P&L', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'total-pnl', window: 50 }, description: 'Cumulative profit/loss' },
  'Win Rate': { label: 'Win Rate', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'win-rate', window: 50 }, description: 'Rolling win rate' },
  'Avg R:R': { label: 'Avg R:R', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'avg-rr', window: 50 }, description: 'Average risk/reward ratio' },
  'Sharpe': { label: 'Sharpe', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'sharpe', window: 50 }, description: 'Risk-adjusted return' },
  'Sortino': { label: 'Sortino', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'sortino', window: 50 }, description: 'Downside risk-adjusted return' },
  'Calmar': { label: 'Calmar', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'calmar', window: 50 }, description: 'Return / max drawdown' },
  'Max Drawdown': { label: 'Max Drawdown', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'max-drawdown', window: 50 }, description: 'Peak-to-trough decline' },
  'Profit Factor': { label: 'Profit Factor', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'profit-factor', window: 50 }, description: 'Gross gain / gross loss' },
  'Kelly %': { label: 'Kelly %', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'kelly-optimal', window: 50 }, description: 'Kelly-optimal bet fraction' },
  'Edge': { label: 'Edge', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'edge', window: 50 }, description: 'Expected value per trade' },
  'Brier Score': { label: 'Brier Score', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'brier-score', window: 50 }, description: 'Prediction calibration' },
  'Trade Count': { label: 'Trade Count', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'trade-count', window: 50 }, description: 'Total trades in window' },
  'SQN': { label: 'SQN', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'sqn', window: 50 }, description: 'System Quality Number' },
  'Recovery Factor': { label: 'Recovery Factor', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'recovery-factor', window: 50 }, description: 'Net profit / max drawdown' },
  'Largest Win': { label: 'Largest Win', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'largest-win', window: 50 }, description: 'Biggest single trade win' },
  'Largest Loss': { label: 'Largest Loss', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'largest-loss', window: 50 }, description: 'Biggest single trade loss' },
  'Consecutive Streak': { label: 'Consecutive Streak', backendType: 'performance', category: 'Performance', color: '#3b82f6', defaultConfig: { metric: 'consecutive-streak', window: 50 }, description: 'Current win/loss streak' },
}

export function getNodeType(label: string): NodeTypeDefinition | undefined {
  return NODE_TYPE_REGISTRY[label]
}

export function getBackendType(label: string): string {
  return NODE_TYPE_REGISTRY[label]?.backendType || 'unknown'
}

export function getDefaultConfig(label: string): Record<string, unknown> {
  return NODE_TYPE_REGISTRY[label]?.defaultConfig || {}
}
