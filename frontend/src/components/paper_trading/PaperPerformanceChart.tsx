import { usePaperPerformance } from '@/hooks/usePaperTrading'

export default function PaperPerformanceChart() {
  const { data: perf, isLoading } = usePaperPerformance()

  if (isLoading) return <div className="rounded-lg border border-gray-700 bg-gray-900 p-4"><p className="text-gray-400">Loading performance...</p></div>
  if (!perf) return null

  function metricColor(value: number, goodThreshold: number, inverse = false): string {
    if (inverse) return value <= goodThreshold ? 'text-green-400' : value <= goodThreshold * 2 ? 'text-yellow-400' : 'text-red-400'
    return value >= goodThreshold ? 'text-green-400' : value >= goodThreshold * 0.5 ? 'text-yellow-400' : 'text-red-400'
  }

  const metrics = [
    { label: 'Total Trades', value: String(perf.total_trades), color: 'text-white' },
    { label: 'Win Rate', value: `${(perf.win_rate * 100).toFixed(1)}%`, color: metricColor(perf.win_rate, 0.5) },
    { label: 'Total P&L', value: `$${perf.total_pnl.toFixed(2)}`, color: perf.total_pnl >= 0 ? 'text-green-400' : 'text-red-400' },
    { label: 'Edge', value: `$${perf.edge.toFixed(2)}`, color: metricColor(perf.edge, 0) },
    { label: 'Sharpe', value: perf.sharpe_ratio.toFixed(2), color: metricColor(perf.sharpe_ratio, 1) },
    { label: 'Avg R:R', value: perf.avg_rr.toFixed(2), color: metricColor(perf.avg_rr, 2) },
    { label: 'Kelly', value: `${(perf.kelly_optimal * 100).toFixed(1)}%`, color: perf.kelly_optimal > 0 ? 'text-green-400' : 'text-gray-500' },
    { label: 'Max DD', value: `${(perf.max_drawdown * 100).toFixed(1)}%`, color: metricColor(perf.max_drawdown, 0.1, true) },
    { label: 'Profit Factor', value: perf.profit_factor.toFixed(2), color: metricColor(perf.profit_factor, 1.5) },
    { label: 'Brier', value: perf.calibration !== null ? perf.calibration.toFixed(4) : '—', color: perf.calibration !== null && perf.calibration <= 0.25 ? 'text-green-400' : 'text-yellow-400' },
  ]

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="text-sm font-semibold uppercase text-gray-400 mb-3">Performance</h3>
      <div className="grid grid-cols-3 gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="rounded bg-gray-950 p-2">
            <p className="text-xs text-gray-500">{m.label}</p>
            <p className={`text-lg font-bold ${m.color}`}>{m.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
