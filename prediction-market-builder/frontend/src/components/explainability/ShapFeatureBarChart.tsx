interface ShapFeatureBarChartProps {
  importance: Record<string, number>
  ranking: string[]
}

function formatPct(v: number): string {
  return (v * 100).toFixed(2) + '%'
}

export default function ShapFeatureBarChart({ importance, ranking }: ShapFeatureBarChartProps) {
  const maxVal = Math.max(0.001, ...Object.values(importance))

  if (ranking.length === 0) {
    return (
      <div className="py-4 text-center text-xs text-gray-500">
        No feature importance data
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {ranking.map((name) => {
        const val = importance[name] || 0
        const pct = (val / maxVal) * 100
        return (
          <div key={name} className="flex items-center gap-2 text-xs">
            <span className="w-28 shrink-0 truncate text-gray-400" title={name}>
              {name}
            </span>
            <div className="relative h-4 flex-1 rounded bg-gray-800">
              <div
                className="absolute inset-y-0 left-0 rounded bg-indigo-500/60"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-14 shrink-0 text-right text-gray-300">
              {formatPct(val)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
