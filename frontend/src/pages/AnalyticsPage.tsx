import { useQuery } from '@tanstack/react-query'
import { fetchAnalyticsSummary, fetchAnalyticsBacktests } from '@/lib/api'
import RiskDashboard from '@/components/analytics/RiskDashboard'

export default function AnalyticsPage() {
  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['analytics-summary'],
    queryFn: fetchAnalyticsSummary,
  })
  const { data: backtests, isLoading: loadingBacktests } = useQuery({
    queryKey: ['analytics-backtests'],
    queryFn: fetchAnalyticsBacktests,
  })

  if (loadingSummary || loadingBacktests) {
    return <div className="p-6"><p className="text-gray-400">Loading analytics...</p></div>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Analytics</h1>

      {summary && (
        <div className="grid grid-cols-4 gap-4">
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Total Trades</p>
            <p className="text-2xl font-bold">{summary.total_trades}</p>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Win Rate</p>
            <p className="text-2xl font-bold text-green-400">{summary.win_rate}%</p>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Winning Trades</p>
            <p className="text-2xl font-bold">{summary.winning_trades}</p>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Total P&L</p>
            <p className={`text-2xl font-bold ${summary.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${summary.total_pnl.toFixed(2)}
            </p>
          </div>
        </div>
      )}

      <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
        <h2 className="mb-3 text-lg font-medium">Backtests</h2>
        {backtests?.backtests?.length > 0 ? (
          backtests.backtests.map((bt: any, i: number) => (
            <div key={i} className="mb-4">
              <p className="font-medium">{bt.name}</p>
              <p className="text-sm text-gray-400">{bt.trades?.length ?? 0} trades</p>
            </div>
          ))
        ) : (
          <p className="text-sm text-gray-400">No backtests recorded yet. Run a strategy to see results here.</p>
        )}
      </div>

      <RiskDashboard />
    </div>
  )
}
