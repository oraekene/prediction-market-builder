import { useState } from 'react'
import { useCompareStrategies } from '@/hooks/usePaperTrading'

export default function StrategyComparison() {
  const [strategyIds, setStrategyIds] = useState('')
  const [activeIds, setActiveIds] = useState<string[]>([])

  const { data, isLoading } = useCompareStrategies(activeIds)

  function handleCompare() {
    const ids = strategyIds.split(',').map((s) => s.trim()).filter(Boolean)
    if (ids.length >= 2) setActiveIds(ids)
  }

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="text-sm font-semibold uppercase text-gray-400 mb-3">Strategy Comparison</h3>

      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={strategyIds}
          onChange={(e) => setStrategyIds(e.target.value)}
          placeholder="strategy-id-1, strategy-id-2, ..."
          className="flex-1 rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
        />
        <button
          onClick={handleCompare}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          Compare
        </button>
      </div>

      {isLoading && <p className="text-sm text-gray-400">Loading comparison...</p>}

      {data?.comparisons && data.comparisons.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-left text-xs uppercase text-gray-500">
                <th className="px-2 py-1 font-medium">Metric</th>
                {data.comparisons.map((_: any, i: number) => (
                  <th key={i} className="px-2 py-1 font-medium">Strategy {i + 1}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {['total_trades', 'win_rate', 'total_pnl', 'edge', 'sharpe_ratio', 'avg_rr', 'kelly_optimal', 'max_drawdown', 'profit_factor', 'avg_return'].map((metric) => (
                <tr key={metric} className="border-b border-gray-800">
                  <td className="px-2 py-1 text-gray-400 capitalize">{metric.replace('_', ' ')}</td>
                  {data.comparisons.map((c: any, i: number) => {
                    const val = c[metric]
                    const display = metric === 'win_rate' || metric === 'max_drawdown' || metric === 'kelly_optimal'
                      ? `${(val * 100).toFixed(1)}%`
                      : metric === 'total_pnl' || metric === 'avg_return'
                        ? `$${val.toFixed(2)}`
                        : val.toFixed(2)
                    const isGood = metric === 'max_drawdown' ? val <= 0.1 : val >= 0
                    return (
                      <td key={i} className={`px-2 py-1 font-mono ${isGood ? 'text-green-400' : 'text-red-400'}`}>
                        {display}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
