import { Link } from 'react-router-dom'
import type { MetaStrategy } from '@/types/meta_strategy'
import { cn } from '@/lib/utils'

interface Props {
  metaStrategy: MetaStrategy
}

const modeLabels: Record<string, string> = {
  standard: 'Standard',
  competition: 'Competition',
  confluence: 'Confluence',
  both: 'Competition + Confluence',
}

export default function MetaStrategyCard({ metaStrategy: ms }: Props) {
  return (
    <Link
      to={`/meta-strategies/${ms.id}`}
      className="block rounded-lg border border-gray-800 bg-gray-900 p-4 transition-colors hover:border-gray-700 hover:bg-gray-800/50"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-white">{ms.name}</h3>
            <span className={cn(
              'rounded-full px-2 py-0.5 text-xs font-medium',
              ms.status === 'active' ? 'bg-green-900/50 text-green-400' : 'bg-gray-800 text-gray-400'
            )}>
              {ms.status}
            </span>
          </div>
          {ms.description && (
            <p className="mt-1 text-sm text-gray-400 line-clamp-2">{ms.description}</p>
          )}
        </div>
        <span className="shrink-0 rounded-full bg-gray-800 px-2 py-0.5 text-xs text-gray-300">
          {modeLabels[ms.mode] || ms.mode}
        </span>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
        <span>{ms.strategy_ids?.length || 0} strategies in pool</span>
        <span className={cn(
          'font-medium',
          ms.current_winner_id ? 'text-green-400' : 'text-gray-500'
        )}>
          {ms.current_winner_id ? 'Active winner' : 'No winner'}
        </span>
      </div>
    </Link>
  )
}
