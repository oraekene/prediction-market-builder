import { useDrawdown } from '@/hooks/useRisk'

export default function DrawdownChart() {
  const { data, isLoading } = useDrawdown()

  if (isLoading) return <p className="text-sm text-gray-400">Loading drawdown...</p>
  if (!data) return null

  const ddPct = ((data.current_drawdown ?? 0) * 100).toFixed(2)
  const maxDdPct = ((data.max_drawdown ?? 0) * 100).toFixed(2)
  const isWarning = (data.current_drawdown ?? 0) > 0.1

  const barWidth = Math.min((data.current_drawdown ?? 0) / Math.max((data.max_drawdown ?? 0.01), 0.01) * 100, 100)

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-300">Drawdown</h3>
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">Current: <span className={isWarning ? 'text-red-400' : 'text-yellow-400'}>{ddPct}%</span></span>
          <span className="text-gray-400">Max: <span className="text-red-400">{maxDdPct}%</span></span>
        </div>
        <div className="h-3 w-full rounded-full bg-gray-700 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${isWarning ? 'bg-red-500' : 'bg-yellow-500'}`}
            style={{ width: `${barWidth}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500">
          <span>Peak: ${data.peak_capital?.toFixed(0)}</span>
          <span>Current: ${data.current_capital?.toFixed(0)}</span>
        </div>
      </div>
    </div>
  )
}
