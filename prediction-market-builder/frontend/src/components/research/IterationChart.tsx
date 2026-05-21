import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface ResultItem {
  iteration: number
  composite_score: number
  backtest_sharpe: number
  backtest_win_rate: number
  verdict: string
}

interface IterationChartProps {
  results: ResultItem[]
}

export function IterationChart({ results }: IterationChartProps) {
  if (results.length === 0) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
        <p className="text-sm text-gray-500">No iteration data for chart</p>
      </div>
    )
  }

  const data = [...results]
    .sort((a, b) => a.iteration - b.iteration)
    .map((r) => ({
      iteration: r.iteration,
      Score: r.composite_score,
      Sharpe: r.backtest_sharpe,
      'Win Rate': r.backtest_win_rate,
    }))

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
      <h2 className="mb-3 text-sm font-semibold text-gray-300">Performance Trends</h2>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="iteration" stroke="#9CA3AF" tick={{ fontSize: 12 }} />
          <YAxis stroke="#9CA3AF" tick={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#F9FAFB' }}
          />
          <Legend />
          <Line type="monotone" dataKey="Score" stroke="#F9FAFB" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="Sharpe" stroke="#3B82F6" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="Win Rate" stroke="#10B981" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
