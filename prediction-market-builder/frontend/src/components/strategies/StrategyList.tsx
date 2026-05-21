import { useStrategies } from '@/hooks/useStrategies'
import { formatTime } from '@/lib/utils'

export default function StrategyList() {
  const { data: strategies, isLoading, error } = useStrategies()

  if (isLoading) {
    return <div className="text-gray-400">Loading strategies...</div>
  }

  if (error) {
    return <div className="text-red-400">Error loading strategies</div>
  }

  if (!strategies || strategies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-500">
        <p className="text-lg">No strategies yet</p>
        <p className="mt-1 text-sm">Click "Create Strategy" to build your first one</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {strategies.map((strategy: any) => (
        <div
          key={strategy.id}
          className="rounded-lg border border-gray-800 bg-gray-950 p-4 hover:border-gray-700"
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
  )
}
