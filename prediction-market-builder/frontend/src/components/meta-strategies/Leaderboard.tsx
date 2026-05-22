import type { StrategyScore } from '@/types/meta_strategy'
import { cn } from '@/lib/utils'

interface Props {
  rankings: StrategyScore[]
  onForcePromote?: (strategyId: string) => void
  winnerId?: string
}

export default function Leaderboard({ rankings, onForcePromote }: Props) {
  if (rankings.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-700 p-8 text-center text-sm text-gray-400">
        No strategies in the pool yet. Add strategies to see rankings.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 bg-gray-950 text-left text-xs uppercase text-gray-500">
            <th className="px-4 py-3 font-medium">Rank</th>
            <th className="px-4 py-3 font-medium">Strategy</th>
            <th className="px-4 py-3 font-medium">Score</th>
            <th className="px-4 py-3 font-medium">Win Rate</th>
            <th className="px-4 py-3 font-medium">Total P&L</th>
            <th className="px-4 py-3 font-medium">Trades</th>
            <th className="px-4 py-3 font-medium">Status</th>
            {onForcePromote && <th className="px-4 py-3 font-medium" />}
          </tr>
        </thead>
        <tbody>
          {rankings.map((s) => (
            <tr
              key={s.id}
              className={cn(
                'border-b border-gray-800 transition-colors',
                s.is_winner ? 'bg-green-900/20' : 'hover:bg-gray-800/50'
              )}
            >
              <td className="px-4 py-3">
                <span className={cn(
                  'flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold',
                  s.rank === 1 ? 'bg-yellow-900/50 text-yellow-400' :
                  s.rank === 2 ? 'bg-gray-700 text-gray-300' :
                  s.rank === 3 ? 'bg-orange-900/50 text-orange-400' :
                  'bg-gray-800 text-gray-500'
                )}>
                  {s.rank}
                </span>
              </td>
              <td className="px-4 py-3 font-medium text-white">{s.name}</td>
              <td className="px-4 py-3 font-mono text-blue-400">{s.score.toFixed(4)}</td>
              <td className="px-4 py-3 font-mono">{(s.win_rate * 100).toFixed(1)}%</td>
              <td className={cn(
                'px-4 py-3 font-mono',
                s.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'
              )}>
                ${s.total_pnl.toFixed(2)}
              </td>
              <td className="px-4 py-3 font-mono text-gray-400">{s.total_trades}</td>
              <td className="px-4 py-3">
                {s.is_winner ? (
                  <span className="rounded-full bg-green-900/50 px-2 py-0.5 text-xs font-medium text-green-400">
                    Winner
                  </span>
                ) : (
                  <span className="text-xs text-gray-500">—</span>
                )}
              </td>
              {onForcePromote && (
                <td className="px-4 py-3">
                  {!s.is_winner && (
                    <button
                      onClick={() => onForcePromote(s.id)}
                      className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-400 hover:bg-gray-700 hover:text-white"
                    >
                      Promote
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
