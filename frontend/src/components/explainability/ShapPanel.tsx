import { ShapExplanation, ShapSummary } from '../../types/explainability'
import ShapWaterfallChart from './ShapWaterfallChart'
import ShapFeatureBarChart from './ShapFeatureBarChart'

interface ShapPanelProps {
  explanation?: ShapExplanation | ShapSummary | null
  compact?: boolean
}

function isFullExplanation(v: any): v is ShapExplanation {
  return v && 'contributions' in v && Array.isArray(v.contributions)
}

function formatPct(v: number): string {
  return (v * 100).toFixed(1) + '%'
}

export default function ShapPanel({ explanation, compact }: ShapPanelProps) {
  if (!explanation) {
    return (
      <div className="rounded border border-gray-800 bg-gray-950 p-3">
        <p className="text-xs text-gray-500">No SHAP explanation available</p>
      </div>
    )
  }

  if (isFullExplanation(explanation)) {
    const baseVal = explanation.base_value
    const outVal = explanation.output_value
    const diff = outVal - baseVal

    return (
      <div className="space-y-3 rounded border border-gray-800 bg-gray-950 p-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            SHAP Explainability
          </h4>
          <span className={`text-xs font-medium ${diff >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {diff >= 0 ? '+' : ''}{formatPct(diff)} from base
          </span>
        </div>

        <div className="flex gap-3 text-xs">
          <div className="rounded bg-gray-900 px-2 py-1">
            <span className="text-gray-500">Base </span>
            <span className="text-gray-200">{formatPct(baseVal)}</span>
          </div>
          <div className="rounded bg-gray-900 px-2 py-1">
            <span className="text-gray-500">Output </span>
            <span className="text-gray-200">{formatPct(outVal)}</span>
          </div>
        </div>

        {compact ? (
          <div className="space-y-1">
            {explanation.ranking.slice(0, 3).map((name) => {
              const imp = explanation.mean_abs_importance[name] || 0
              return (
                <div key={name} className="flex items-center justify-between text-xs">
                  <span className="text-gray-400">{name}</span>
                  <span className="text-gray-300">{formatPct(imp)}</span>
                </div>
              )
            })}
          </div>
        ) : (
          <>
            <ShapWaterfallChart explanation={explanation} />
            <ShapFeatureBarChart
              importance={explanation.mean_abs_importance}
              ranking={explanation.ranking}
            />
          </>
        )}
      </div>
    )
  }

  const shapSummary = explanation as ShapSummary
  return (
    <div className="space-y-2 rounded border border-gray-800 bg-gray-950 p-3">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500">
        SHAP Summary
      </h4>
      <div className="flex gap-3 text-xs">
        {shapSummary.base_value != null && (
          <div className="rounded bg-gray-900 px-2 py-1">
            <span className="text-gray-500">Base </span>
            <span className="text-gray-200">{formatPct(shapSummary.base_value)}</span>
          </div>
        )}
        {shapSummary.output_value != null && (
          <div className="rounded bg-gray-900 px-2 py-1">
            <span className="text-gray-500">Output </span>
            <span className="text-gray-200">{formatPct(shapSummary.output_value)}</span>
          </div>
        )}
      </div>
      {shapSummary.top_features && shapSummary.top_features.length > 0 && (
        <div className="space-y-1">
          <span className="text-[10px] font-medium text-gray-500">Top contributors</span>
          {shapSummary.top_features.map((f) => {
            const isPos = f.shap_value >= 0
            return (
              <div key={f.name} className="flex items-center justify-between text-xs">
                <span className="text-gray-400">{f.name}</span>
                <span className={isPos ? 'text-green-400' : 'text-red-400'}>
                  {isPos ? '+' : ''}{formatPct(f.shap_value)}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
