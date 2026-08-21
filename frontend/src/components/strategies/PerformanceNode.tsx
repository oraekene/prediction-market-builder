import { Handle, Position } from '@xyflow/react'

const metricLabel: Record<string, string> = {
  'current-balance': 'Balance',
  'total-pnl': 'Total P&L',
  'win-rate': 'Win Rate',
  'avg-rr': 'Avg R:R',
  sharpe: 'Sharpe',
  sortino: 'Sortino',
  calmar: 'Calmar',
  'max-drawdown': 'Max DD',
  'profit-factor': 'Profit Factor',
  'kelly-optimal': 'Kelly %',
  edge: 'Edge',
  'brier-score': 'Brier Score',
  'trade-count': 'Trades',
  sqn: 'SQN',
  'recovery-factor': 'Recovery F.',
  'largest-win': 'Largest Win',
  'largest-loss': 'Largest Loss',
  'consecutive-streak': 'Streak',
}

export default function PerformanceNode({ data }: { data: Record<string, unknown> }) {
  const metric = (data.metric as string) || ''
  const fallbackLabel = typeof data.label === 'string' ? data.label : ''
  const label: string = metricLabel[metric] || fallbackLabel || metric
  const value = data.value as number | null | undefined
  const windowSize = data.window as number | undefined

  return (
    <div className="rounded-md border border-blue-600/40 bg-gray-900 px-3 py-2 shadow-lg min-w-[140px]">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[10px] font-medium uppercase tracking-wider text-blue-400">PERF</span>
        <span className="text-xs text-gray-300">{label}</span>
      </div>
      <div className="text-lg font-bold text-white tabular-nums">
        {value !== null && value !== undefined ? formatValue(metric, value) : '—'}
      </div>
      {windowSize != null && windowSize > 0 && (
        <div className="text-[10px] text-gray-600 mt-0.5">window: {windowSize}</div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-blue-500 !w-2 !h-2" />
    </div>
  )
}

export function formatValue(metric: string, value: number): string {
  if (['win-rate', 'kelly-optimal', 'max-drawdown'].includes(metric)) {
    return `${(value * 100).toFixed(1)}%`
  }
  if (['total-pnl', 'edge', 'largest-win', 'largest-loss', 'avg-return', 'current-balance'].includes(metric)) {
    return `$${value.toFixed(2)}`
  }
  if (['trade-count', 'consecutive-streak'].includes(metric)) {
    return String(value)
  }
  return value.toFixed(4)
}
