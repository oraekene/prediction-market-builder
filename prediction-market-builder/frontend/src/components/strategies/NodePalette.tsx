const performanceItems: { label: string; metric: string }[] = [
  { label: 'Current Balance', metric: 'current-balance' },
  { label: 'Total P&L', metric: 'total-pnl' },
  { label: 'Win Rate', metric: 'win-rate' },
  { label: 'Avg R:R', metric: 'avg-rr' },
  { label: 'Sharpe', metric: 'sharpe' },
  { label: 'Sortino', metric: 'sortino' },
  { label: 'Calmar', metric: 'calmar' },
  { label: 'Max Drawdown', metric: 'max-drawdown' },
  { label: 'Profit Factor', metric: 'profit-factor' },
  { label: 'Kelly %', metric: 'kelly-optimal' },
  { label: 'Edge', metric: 'edge' },
  { label: 'Brier Score', metric: 'brier-score' },
  { label: 'Trade Count', metric: 'trade-count' },
  { label: 'SQN', metric: 'sqn' },
  { label: 'Recovery Factor', metric: 'recovery-factor' },
  { label: 'Largest Win', metric: 'largest-win' },
  { label: 'Largest Loss', metric: 'largest-loss' },
  { label: 'Consecutive Streak', metric: 'consecutive-streak' },
]

const nodeCategories: { category: string; items: string[] }[] = [
  { category: 'Sources', items: ['Polymarket', 'Kalshi', 'Drift', 'Web Search', 'News'] },
  { category: 'Filters', items: ['TabPFN Signal', 'Toto-2 Climate', 'Sentiment', 'SHAP Feature Importance'] },
  { category: 'Conditions', items: ['Threshold', 'Time-Based', 'AND/OR', 'Branch'] },
  { category: 'Actions', items: ['Place Bet', 'Send Alert', 'Forward', 'Webhook', 'Close Position', 'Convert to Stablecoin'] },
  { category: 'Risk - Position Exits', items: [
    'Stop-Loss', 'Take Profit', 'Trailing Stop', 'Tightening Trailing Stop',
    'ATR Stop', 'Volatility Stop', 'Break-Even Stop', 'Time Exit',
    'Scaling Exit', 'Moving Average Exit',
  ]},
  { category: 'Risk - Portfolio Limits', items: [
    'Drawdown', 'VaR Check', 'Expected Shortfall', 'Daily Loss Limit',
    'Weekly Loss Limit', 'Monthly Loss Limit', 'Max Position Count',
    'Max Gross Exposure', 'Max Net Exposure', 'Leverage Limit',
    'Sector Exposure Limit', 'Beta Exposure Limit', 'Volatility Targeting',
    'Stress Test', 'Monte Carlo Risk', 'Tail Risk Check', 'Liquidity Risk',
  ]},
  { category: 'Risk - Diversification', items: [
    'Correlation Check', 'Concentration Check', 'Factor Exposure',
    'MCR Check', 'Worst Case Portfolio',
  ]},
  { category: 'Risk - Greeks', items: [
    'Delta Exposure', 'Gamma Exposure', 'Vega Exposure',
    'Theta Decay', 'Vanna Exposure', 'Volga Exposure',
  ]},
  { category: 'Risk - Execution', items: [
    'Circuit Breaker', 'Slippage Guard', 'Max Consecutive Losses',
    'Cooldown Period', 'Position Timeout',
  ]},
  { category: 'Risk - Regime', items: [
    'Volatility Regime', 'Correlation Regime Shift', 'Toxicity Detection',
    'Order Flow Imbalance',
  ]},
  { category: 'Risk - Portfolio Construction', items: [
    'Kelly Criterion', 'Risk Parity', 'Mean-Variance Optimization',
    'Black-Litterman', 'Hierarchical Risk Parity',
  ]},
  { category: 'Auto-Withdrawal', items: [
    'Withdraw to Safe Wallet', 'Withdrawal Strategy',
  ]},
  { category: 'Analysis', items: ['Bayesian Inference', 'Monte Carlo', 'Backtest', 'SHAP Explainability'] },
]

export default function NodePalette() {
  function onDragStart(event: React.DragEvent, label: string, nodeFlowType: string) {
    event.dataTransfer.setData('application/reactflow', label)
    event.dataTransfer.setData('application/reactflow-type', nodeFlowType)
    event.dataTransfer.effectAllowed = 'move'
  }

  return (
    <aside className="w-56 border-r border-gray-800 bg-gray-950 p-3 overflow-y-auto">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Nodes</h3>
      {nodeCategories.map((group) => (
        <div key={group.category} className="mb-3">
          <h4 className="mb-1 text-[10px] font-medium uppercase text-gray-600">{group.category}</h4>
          <div className="space-y-1">
            {group.items.map((item) => (
              <div
                key={item}
                draggable
                onDragStart={(e) => onDragStart(e, item, 'default')}
                className="cursor-grab rounded border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-xs text-gray-300 transition-colors hover:border-blue-500 hover:text-white active:cursor-grabbing"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      ))}
      <div className="mb-3">
        <h4 className="mb-1 text-[10px] font-medium uppercase text-gray-600">Performance</h4>
        <div className="space-y-1">
          {performanceItems.map((item) => (
            <div
              key={item.label}
              draggable
              onDragStart={(e) => onDragStart(e, item.label, 'performance')}
              className="cursor-grab rounded border border-blue-800/40 bg-gray-800 px-2.5 py-1.5 text-xs text-gray-300 transition-colors hover:border-blue-500 hover:text-white active:cursor-grabbing"
            >
              {item.label}
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}
