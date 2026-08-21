import type { NodeCanvasNode } from './NodeCanvas'

interface Props {
  selectedNode: NodeCanvasNode | null
  onNodeUpdate?: (nodeId: string, newData: Record<string, unknown>) => void
}

const performanceMetrics: Record<string, { label: string; description: string }> = {
  'current-balance': { label: 'Current Balance', description: 'Current wallet balance' },
  'total-pnl': { label: 'Total P&L', description: 'Cumulative profit/loss' },
  'win-rate': { label: 'Win Rate', description: 'Rolling win rate (0-1)' },
  'avg-rr': { label: 'Avg R:R', description: 'Average risk/reward ratio' },
  'sharpe': { label: 'Sharpe Ratio', description: 'Risk-adjusted return' },
  'sortino': { label: 'Sortino Ratio', description: 'Downside risk-adjusted return' },
  'calmar': { label: 'Calmar Ratio', description: 'Return / max drawdown' },
  'max-drawdown': { label: 'Max Drawdown', description: 'Peak-to-trough decline (0-1)' },
  'profit-factor': { label: 'Profit Factor', description: 'Gross gain / gross loss' },
  'kelly-optimal': { label: 'Kelly %', description: 'Kelly-optimal bet fraction (0-1)' },
  'edge': { label: 'Edge', description: 'Expected value per trade' },
  'brier-score': { label: 'Brier Score', description: 'Prediction calibration' },
  'trade-count': { label: 'Trade Count', description: 'Total trades in window' },
  'sqn': { label: 'SQN', description: 'System Quality Number' },
  'recovery-factor': { label: 'Recovery Factor', description: 'Net profit / max drawdown' },
  'largest-win': { label: 'Largest Win', description: 'Biggest single trade win' },
  'largest-loss': { label: 'Largest Loss', description: 'Biggest single trade loss' },
  'consecutive-streak': { label: 'Consecutive Streak', description: 'Current win/loss streak' },
}

export default function NodePropertyPanel({ selectedNode, onNodeUpdate }: Props) {
  if (!selectedNode) {
    return (
      <aside className="w-64 border-l border-gray-800 bg-gray-950 p-4">
        <p className="text-sm text-gray-500">Select a node to configure</p>
      </aside>
    )
  }

  const isPerformance = selectedNode.type === 'performance'
  const metric = selectedNode.data.metric as string | undefined
  const meta = metric ? performanceMetrics[metric] : null

  const handleFieldChange = (key: string, value: unknown) => {
    if (onNodeUpdate) {
      onNodeUpdate(selectedNode.id, { [key]: value })
    }
  }

  return (
    <aside className="w-64 border-l border-gray-800 bg-gray-950 p-4 overflow-y-auto">
      <h3 className="mb-4 text-sm font-semibold text-white">
        Configure: {selectedNode.data.label}
      </h3>
      <div className="space-y-4">
        {/* Node label */}
        <label className="block">
          <span className="text-xs text-gray-400">Label</span>
          <input
            type="text"
            value={(selectedNode.data.label as string) || ''}
            onChange={(e) => handleFieldChange('label', e.target.value)}
            className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
          />
        </label>

        {/* Backend type display */}
        {selectedNode.data.backendType && (
          <div className="rounded bg-gray-800/50 p-2">
            <span className="text-[10px] text-gray-500">Handler: </span>
            <span className="text-[10px] font-mono text-blue-400">{selectedNode.data.backendType as string}</span>
          </div>
        )}

        {isPerformance && meta && (
          <>
            <div className="rounded bg-blue-900/20 border border-blue-800/30 p-2">
              <p className="text-xs text-blue-300 font-medium">{meta.label}</p>
              <p className="text-[10px] text-blue-400/70 mt-0.5">{meta.description}</p>
            </div>
            <label className="block">
              <span className="text-xs text-gray-400">Window (trades)</span>
              <input
                type="number"
                min={0}
                max={5000}
                value={(selectedNode.data.window as number) ?? 50}
                onChange={(e) => handleFieldChange('window', parseInt(e.target.value) || 0)}
                className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
              <p className="text-[10px] text-gray-600 mt-0.5">0 = all trades, 50+ for rolling metrics</p>
            </label>
            <div className="border-t border-gray-800 pt-4">
              <h4 className="mb-2 text-xs font-medium text-gray-500">Output</h4>
              <span className="rounded bg-gray-800 px-2 py-0.5 text-xs text-blue-400">Float (Number)</span>
              <p className="text-[10px] text-gray-600 mt-1">Connects to Condition nodes (Threshold, Branch)</p>
            </div>
          </>
        )}

        {!isPerformance && (
          <>
            <label className="block">
              <span className="text-xs text-gray-400">Parameter</span>
              <input
                type="text"
                value={(selectedNode.data.parameter as string) || ''}
                onChange={(e) => handleFieldChange('parameter', e.target.value)}
                className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                placeholder="Value"
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Description</span>
              <textarea
                value={(selectedNode.data.description as string) || ''}
                onChange={(e) => handleFieldChange('description', e.target.value)}
                className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                rows={3}
                placeholder="Optional description"
              />
            </label>
            <div className="border-t border-gray-800 pt-4">
              <h4 className="mb-2 text-xs font-medium text-gray-500">Output Type</h4>
              <span className="rounded bg-gray-800 px-2 py-0.5 text-xs text-blue-400">
                {selectedNode.type === 'default' ? 'Data' : 'Mixed'}
              </span>
            </div>
          </>
        )}
      </div>
    </aside>
  )
}
