import { useState } from 'react'
import type { MetaStrategy, ScoringConfig, PromotionConfig, ConfluenceConfig, MetaStrategyConsumer } from '@/types/meta_strategy'
import { DEFAULT_SCORING_CONFIG, DEFAULT_PROMOTION_CONFIG, DEFAULT_CONFLUENCE_CONFIG } from '@/types/meta_strategy'
import { useUpdateMetaStrategy, useAddStrategyToMetaPool, useRemoveStrategyFromMetaPool } from '@/hooks/useMetaStrategies'
import { useStrategies } from '@/hooks/useStrategies'

interface Props {
  metaStrategy: MetaStrategy
}

export default function MetaStrategyConfig({ metaStrategy: ms }: Props) {
  const update = useUpdateMetaStrategy()
  const addToPool = useAddStrategyToMetaPool()
  const removeFromPool = useRemoveStrategyFromMetaPool()
  const { data: allStrategies } = useStrategies()
  const strategies = Array.isArray(allStrategies) ? allStrategies : []

  const [editMode, setEditMode] = useState(false)
  const [name, setName] = useState(ms.name)
  const [mode, setMode] = useState(ms.mode)
  const [consumer, setConsumer] = useState<MetaStrategyConsumer | ''>(ms.consumer || '')

  const [scoring, setScoring] = useState<ScoringConfig>(ms.scoring_config || DEFAULT_SCORING_CONFIG)
  const [promotion, setPromotion] = useState<PromotionConfig>(ms.promotion_config || DEFAULT_PROMOTION_CONFIG)
  const [confluence, setConfluence] = useState<ConfluenceConfig>(ms.confluence_config || DEFAULT_CONFLUENCE_CONFIG)

  const availableStrategies = strategies.filter(
    (s: any) => !ms.strategy_ids.includes(s.id)
  )

  async function handleSave() {
    await update.mutateAsync({
      id: ms.id,
      data: {
        name,
        mode,
        consumer: consumer || null,
        scoring_config: scoring,
        promotion_config: promotion,
        confluence_config: confluence,
      },
    })
    setEditMode(false)
  }

  async function handleAddStrategy(strategyId: string) {
    await addToPool.mutateAsync({ msId: ms.id, strategyId })
  }

  async function handleRemoveStrategy(strategyId: string) {
    await removeFromPool.mutateAsync({ msId: ms.id, strategyId })
  }

  function updateScoringMetric(key: keyof ScoringConfig['metrics'], value: number) {
    setScoring({
      ...scoring,
      metrics: { ...scoring.metrics, [key]: value },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Configuration</h2>
        <button
          onClick={() => (editMode ? handleSave() : setEditMode(true))}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          {editMode ? 'Save' : 'Edit'}
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <label className="text-xs font-medium uppercase text-gray-500">Name</label>
          {editMode ? (
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
            />
          ) : (
            <p className="text-sm text-white">{ms.name}</p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium uppercase text-gray-500">Mode</label>
          {editMode ? (
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as any)}
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
            >
              {(['competition', 'confluence', 'both', 'standard'] as const).map((o) => (
                <option key={o} value={o}>{o}</option>
              ))}
            </select>
          ) : (
            <p className="text-sm text-white capitalize">{ms.mode}</p>
          )}
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium uppercase text-gray-500">Consumer</label>
          {editMode ? (
            <select
              value={consumer}
              onChange={(e) => setConsumer(e.target.value as MetaStrategyConsumer | '')}
              className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
            >
              <option value="">Not set</option>
              <option value="paper_trading">Paper Trading</option>
              <option value="live">Live Execution</option>
              <option value="backtesting">Backtesting</option>
              <option value="copy_trading">Copy Trading</option>
            </select>
          ) : (
            <p className="text-sm text-white">{ms.consumer || 'Not set'}</p>
          )}
        </div>
      </div>

      {editMode && (
        <>
          <div className="space-y-3 rounded-lg border border-gray-800 p-4">
            <h3 className="text-sm font-semibold text-white">Scoring Weights</h3>
            <p className="text-xs text-gray-500">These weights are used by the default scorer. For custom scoring, build a scoring pipeline in the node graph.</p>
            <div className="grid gap-3 sm:grid-cols-2">
              {(['sharpe', 'win_rate', 'profit_factor', 'max_drawdown', 'confidence', 'expected_value', 'signal_strength', 'consistency'] as const).map((key) => (
                <div key={key} className="space-y-1">
                  <label className="text-xs text-gray-400 capitalize">{key.replace('_', ' ')}</label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    value={scoring.metrics[key]}
                    onChange={(e) => updateScoringMetric(key, parseFloat(e.target.value) || 0)}
                    className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3 rounded-lg border border-gray-800 p-4">
            <h3 className="text-sm font-semibold text-white">Promotion Schedule</h3>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <label className="text-xs text-gray-400">Interval</label>
                <select
                  value={promotion.interval}
                  onChange={(e) => setPromotion({ ...promotion, interval: e.target.value as any })}
                  className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              {promotion.interval === 'custom' && (
                <div className="space-y-1">
                  <label className="text-xs text-gray-400">Interval (days)</label>
                  <input
                    type="number"
                    min="1"
                    value={promotion.interval_days || ''}
                    onChange={(e) => setPromotion({ ...promotion, interval_days: parseInt(e.target.value) || null })}
                    className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
                  />
                </div>
              )}
              <div className="space-y-1">
                <label className="text-xs text-gray-400">Evaluation Window (days)</label>
                <input
                  type="number"
                  min="1"
                  value={promotion.evaluation_window_days}
                  onChange={(e) => setPromotion({ ...promotion, evaluation_window_days: parseInt(e.target.value) || 30 })}
                  className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-400">Probation (hours)</label>
                <input
                  type="number"
                  min="0"
                  value={promotion.probation_hours}
                  onChange={(e) => setPromotion({ ...promotion, probation_hours: parseInt(e.target.value) || 0 })}
                  className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
                />
              </div>
            </div>
          </div>

          <div className="space-y-3 rounded-lg border border-gray-800 p-4">
            <h3 className="text-sm font-semibold text-white">Confluence Settings</h3>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <label className="text-xs text-gray-400">Threshold</label>
                <input
                  type="number"
                  min="1"
                  value={confluence.threshold}
                  onChange={(e) => setConfluence({ ...confluence, threshold: parseInt(e.target.value) || 1 })}
                  className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-400">Source</label>
                <select
                  value={confluence.source}
                  onChange={(e) => setConfluence({ ...confluence, source: e.target.value as any })}
                  className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
                >
                  <option value="top_n">Top N</option>
                  <option value="manual">Manual Selection</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-gray-400">From Top N</label>
                <input
                  type="number"
                  min="1"
                  value={confluence.from_top}
                  onChange={(e) => setConfluence({ ...confluence, from_top: parseInt(e.target.value) || 1 })}
                  className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
                />
              </div>
            </div>
          </div>
        </>
      )}

      <div className="space-y-2">
        <label className="text-xs font-medium uppercase text-gray-500">Strategy Pool</label>
        <div className="rounded-lg border border-gray-800 p-4">
          {ms.strategy_ids.length === 0 ? (
            <p className="text-sm text-gray-500">No strategies in pool.</p>
          ) : (
            <div className="space-y-2">
              {ms.strategy_ids.map((sid) => {
                const strat = strategies.find((s: any) => s.id === sid)
                return (
                  <div key={sid} className="flex items-center justify-between rounded-md bg-gray-800 px-3 py-2">
                    <span className="text-sm text-white">{strat?.name || sid}</span>
                    <button
                      onClick={() => handleRemoveStrategy(sid)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      Remove
                    </button>
                  </div>
                )
              })}
            </div>
          )}

          {availableStrategies.length > 0 && (
            <div className="mt-3 border-t border-gray-700 pt-3">
              <label className="mb-1 block text-xs text-gray-500">Add strategy to pool:</label>
              <select
                onChange={(e) => {
                  if (e.target.value) handleAddStrategy(e.target.value)
                  e.target.value = ''
                }}
                className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white"
              >
                <option value="">Select a strategy...</option>
                {availableStrategies.map((s: any) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
