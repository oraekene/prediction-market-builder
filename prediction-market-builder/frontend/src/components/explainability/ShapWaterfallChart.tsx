import { ShapExplanation } from '../../types/explainability'

interface ShapWaterfallChartProps {
  explanation: ShapExplanation
}

function formatPct(v: number): string {
  return (v * 100).toFixed(1) + '%'
}

export default function ShapWaterfallChart({ explanation }: ShapWaterfallChartProps) {
  const { base_value, output_value, contributions } = explanation

  const ranked = [...contributions].sort(
    (a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value)
  )

  const maxBar = Math.max(
    Math.abs(base_value - output_value),
    ...ranked.map(c => Math.abs(c.shap_value)),
    0.01
  )

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>Base: {formatPct(base_value)}</span>
        <span>Prediction: {formatPct(output_value)}</span>
      </div>
      <div className="relative h-5 w-full rounded bg-gray-800">
        <div
          className="absolute inset-y-0 rounded bg-blue-500 transition-all"
          style={{
            left: `${(base_value / (maxBar * 2)) * 50}%`,
            width: `${Math.abs((output_value - base_value) / (maxBar * 2)) * 50}%`,
            backgroundColor: output_value >= base_value ? '#22c55e' : '#ef4444',
          }}
        />
        <div
          className="absolute inset-y-0 w-0.5 bg-white"
          style={{ left: `${50 + (base_value / maxBar - 1) * 50}%` }}
        />
        <div
          className="absolute inset-y-0 w-0.5 bg-yellow-400"
          style={{ left: `${50 + (output_value / maxBar - 1) * 50}%` }}
        />
      </div>
      <div className="space-y-0.5">
        {ranked.map((c) => {
          const isPositive = c.shap_value >= 0
          const barWidth = Math.abs(c.shap_value) / maxBar * 100
          return (
            <div key={c.name} className="flex items-center gap-2 text-xs">
              <span className="w-28 shrink-0 truncate text-gray-400" title={c.name}>
                {c.name}
              </span>
              <div className="relative h-3 flex-1 rounded bg-gray-800">
                <div
                  className={`absolute inset-y-0 rounded ${isPositive ? 'bg-green-500/60' : 'bg-red-500/60'}`}
                  style={{
                    [isPositive ? 'left' : 'right']: '50%',
                    width: `${barWidth / 2}%`,
                  }}
                />
              </div>
              <span className={`w-16 shrink-0 text-right ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                {isPositive ? '+' : ''}{formatPct(c.shap_value)}
              </span>
              <span className="w-14 shrink-0 text-right text-gray-500">
                {formatPct(c.feature_value)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
