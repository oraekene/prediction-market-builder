import { usePaperPerformance } from '@/hooks/usePaperTrading'

export default function PaperPerformanceChart() {
  const { data: perf, isLoading } = usePaperPerformance()

  if (isLoading) return <div className="rounded-lg border border-gray-700 bg-gray-900 p-4"><p className="text-gray-400">Loading performance...</p></div>
  if (!perf) return null

  const metrics = [
    { label: 'Total Trades', value: perf.total_trades, color: 'text-white' },
    { label: 'Win Rate', value: ${(perf.win_rate * 100).toFixed(1)}%, color: perf.win_rate >= 0.5 ? 'text-green-400' : 'text-red-400' },
    { label: 'Total P&L', value: $, color: perf.total_pnl >= 0 ? 'text-green-400' : 'text-red-400' },
    { label: 'Sharpe Ratio', value: perf.sharpe_ratio.toFixed(2), color: perf.sharpe_ratio >= 1 ? 'text-green-400' : 'text-yellow-400' },
    { label: 'Max Drawdown', value: ${(perf.max_drawdown * 100).toFixed(1)}%, color: 'text-red-400' },
    { label: 'Profit Factor', value: perf.profit_factor.toFixed(2), color: perf.profit_factor >= 1.5 ? 'text-green-400' : 'text-yellow-400' },
    { label: 'Avg Return', value: $, color: perf.avg_return >= 0 ? 'text-green-400' : 'text-red-400' },
    { label: 'Winning', value: perf.winning_trades, color: 'text-green-400' },
    { label: 'Losing', value: perf.losing_trades, color: 'text-red-400' },
  ]

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="text-sm font-semibold uppercase text-gray-400 mb-3">Performance</h3>
      <div className="grid grid-cols-3 gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="rounded bg-gray-950 p-2">
            <p className="text-xs text-gray-500">{m.label}</p>
            <p className={	ext-lg font-bold }>{m.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
