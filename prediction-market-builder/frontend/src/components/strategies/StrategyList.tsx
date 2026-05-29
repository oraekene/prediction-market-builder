import { useStrategies, useCreateStrategy } from '@/hooks/useStrategies'
import { formatTime } from '@/lib/utils'
import { useState } from 'react'

interface StrategyItem {
  id: string
  name: string
  description?: string | null
  status: string
  mode: string
  created_at?: string | null
}

const TEMPLATES = [
  {
    name: 'Momentum Follow',
    description: 'Buy when odds rise above 60%, sell when they drop below 40%. Simple trend-following strategy.',
  },
  {
    name: 'Mean Reversion',
    description: 'Bet against extreme odds (>80% or <20%). Assumes markets overreact.',
  },
  {
    name: 'News Sentiment',
    description: 'Trades based on news sentiment analysis. Buys positive, sells negative.',
  },
]

interface StrategyListProps {
  onEditStrategy?: (strategyId: string) => void
}

export default function StrategyList({ onEditStrategy }: StrategyListProps) {
  const [showTemplates, setShowTemplates] = useState(false)
  const { data: strategies, isLoading, error } = useStrategies()
  const createStrategy = useCreateStrategy()

  if (isLoading) {
    return <div className="text-gray-400">Loading strategies...</div>
  }

  if (error) {
    return <div className="text-red-400">Error loading strategies</div>
  }

  const isEmpty = !strategies || strategies.length === 0

  return (
    <div>
      {/* Empty state */}
      {isEmpty && !showTemplates && (
        <div className="flex flex-col items-center justify-center py-16 text-gray-500">
          <div className="mb-4 text-5xl">🧠</div>
          <p className="text-lg">No strategies yet</p>
          <p className="mt-1 text-sm">Click "Create Strategy" to build your first one</p>
          <p className="mt-1 text-sm">or</p>
          <button
            onClick={() => setShowTemplates(true)}
            className="mt-3 rounded-md border border-blue-600 px-4 py-2 text-sm text-blue-400 hover:bg-blue-600 hover:text-white transition-colors"
          >
            Start from a template
          </button>
        </div>
      )}

      {/* Template picker */}
      {isEmpty && showTemplates && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Quick-start Templates</h2>
            <button
              onClick={() => setShowTemplates(false)}
              className="text-xs text-gray-500 hover:text-white"
            >
              Back to empty state
            </button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {TEMPLATES.map((tpl) => (
              <div
                key={tpl.name}
                className="rounded-lg border border-gray-800 bg-gray-950 p-4 hover:border-gray-700 transition-colors cursor-pointer"
                onClick={() => {
                  createStrategy.mutate({
                    name: tpl.name,
                    description: tpl.description,
                    mode: 'paper',
                    nodes: [],
                  })
                }}
              >
                <h3 className="font-medium text-white">{tpl.name}</h3>
                <p className="mt-2 text-sm text-gray-400">{tpl.description}</p>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    createStrategy.mutate({
                      name: tpl.name,
                      description: tpl.description,
                      mode: 'paper',
                      nodes: [],
                    })
                  }}
                  className="mt-3 rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700"
                >
                  Use template
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strategy grid */}
      {!isEmpty && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {strategies.map((strategy: StrategyItem) => (
            <div
              key={strategy.id}
              onClick={() => onEditStrategy?.(strategy.id)}
              className="rounded-lg border border-gray-800 bg-gray-950 p-4 hover:border-blue-600/50 transition-colors cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-white truncate">{strategy.name}</h3>
                <span className={`rounded-full px-2 py-0.5 text-xs capitalize ${
                  strategy.status === 'active' ? 'bg-green-900 text-green-400' :
                  strategy.status === 'paused' ? 'bg-yellow-900 text-yellow-400' :
                  'bg-gray-800 text-gray-400'
                }`}>
                  {strategy.status}
                </span>
              </div>
              {strategy.description && (
                <p className="mt-2 text-sm text-gray-400 line-clamp-2">{strategy.description}</p>
              )}
              <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                <span className="capitalize">{strategy.mode} mode</span>
                <span>{strategy.created_at ? formatTime(strategy.created_at) : ''}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
