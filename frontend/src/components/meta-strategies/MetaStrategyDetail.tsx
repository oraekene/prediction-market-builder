import { useParams, useNavigate } from 'react-router-dom'
import {
  useMetaStrategy,
  useMetaRankings,
  useEvaluateMetaPromotion,
  useForceMetaPromote,
  useDeleteMetaStrategy,
  useMetaPerformance,
} from '@/hooks/useMetaStrategies'
import Leaderboard from './Leaderboard'
import MetaStrategyConfig from './MetaStrategyConfig'

export default function MetaStrategyDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: ms, isLoading, error } = useMetaStrategy(id!)
  const { data: rankingsData, isLoading: rankingsLoading } = useMetaRankings(id!)
  const { data: performanceData } = useMetaPerformance(id!)
  const evaluate = useEvaluateMetaPromotion()
  const forcePromote = useForceMetaPromote()
  const deleteMs = useDeleteMetaStrategy()

  if (isLoading) return <div className="text-gray-400">Loading meta-strategy...</div>
  if (error || !ms) return <div className="text-red-400">Meta-strategy not found</div>

  const rankings = rankingsData?.rankings || []
  const perf = performanceData

  async function handleEvaluate() {
    await evaluate.mutateAsync(id!)
  }

  async function handleForcePromote(strategyId: string) {
    await forcePromote.mutateAsync({ msId: id!, strategyId })
  }

  async function handleDelete() {
    if (!confirm('Delete this meta-strategy? This cannot be undone.')) return
    await deleteMs.mutateAsync(id!)
    navigate('/meta-strategies')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate('/meta-strategies')}
            className="mb-2 text-sm text-gray-500 hover:text-white"
          >
            &larr; Back to Meta-Strategies
          </button>
          <h1 className="text-xl font-semibold text-white">{ms.name}</h1>
          {ms.description && <p className="mt-1 text-sm text-gray-400">{ms.description}</p>}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleEvaluate}
            disabled={evaluate.isPending}
            className="rounded-md bg-green-700 px-3 py-1.5 text-sm text-white hover:bg-green-600 disabled:opacity-50"
          >
            {evaluate.isPending ? 'Evaluating...' : 'Run Evaluation'}
          </button>
          <button
            onClick={handleDelete}
            className="rounded-md bg-red-900/50 px-3 py-1.5 text-sm text-red-400 hover:bg-red-800/50"
          >
            Delete
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <div className="flex flex-wrap items-center gap-6 text-sm">
          <div>
            <span className="text-gray-500">Mode:</span>{' '}
            <span className="text-white capitalize">{ms.mode}</span>
          </div>
          <div>
            <span className="text-gray-500">Status:</span>{' '}
            <span className="text-white capitalize">{ms.status}</span>
          </div>
          <div>
            <span className="text-gray-500">Consumer:</span>{' '}
            <span className="text-white">{ms.consumer || 'Not set'}</span>
          </div>
          <div>
            <span className="text-gray-500">Winner:</span>{' '}
            <span className={ms.current_winner_id ? 'text-green-400' : 'text-gray-500'}>
              {ms.current_winner_id || 'None selected'}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Last promoted:</span>{' '}
            <span className="text-gray-400">
              {ms.last_promotion_at
                ? new Date(ms.last_promotion_at).toLocaleDateString()
                : 'Never'}
            </span>
          </div>
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-white">Leaderboard</h2>
        {rankingsLoading ? (
          <div className="text-gray-400">Loading rankings...</div>
        ) : (
          <Leaderboard
            rankings={rankings}
            onForcePromote={handleForcePromote}
            winnerId={ms.current_winner_id}
          />
        )}
      </div>

      {perf && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-white">Performance</h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
              <p className="text-xs text-gray-500">Total P&L</p>
              <p className={`text-xl font-bold font-mono ${perf.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                ${perf.total_pnl.toFixed(2)}
              </p>
            </div>
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
              <p className="text-xs text-gray-500">Total Trades</p>
              <p className="text-xl font-bold font-mono text-white">{perf.total_trades}</p>
            </div>
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
              <p className="text-xs text-gray-500">Overall Win Rate</p>
              <p className="text-xl font-bold font-mono text-white">
                {(perf.overall_win_rate * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>
      )}

      <MetaStrategyConfig metaStrategy={ms} />
    </div>
  )
}
