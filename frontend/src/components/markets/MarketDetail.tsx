import { useQuery } from '@tanstack/react-query'
import { fetchMarket } from '@/lib/api'
import { formatOdds, formatVolume, formatTime } from '@/lib/utils'

interface MarketDetailProps {
  marketId: string
}

export default function MarketDetail({ marketId }: MarketDetailProps) {
  const { data: market, isLoading, error } = useQuery({
    queryKey: ['market', marketId],
    queryFn: () => fetchMarket(marketId),
    enabled: !!marketId,
  })

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
        <p className="text-gray-500">Loading market...</p>
      </div>
    )
  }

  if (error || !market) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
        <p className="text-red-400">Failed to load market</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950 p-4 space-y-3">
      <h2 className="text-lg font-semibold text-white">{market.title}</h2>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-gray-500">Platform</span>
          <p className="text-white capitalize">{market.platform}</p>
        </div>
        <div>
          <span className="text-gray-500">Category</span>
          <p className="text-white">{market.category || '-'}</p>
        </div>
        <div>
          <span className="text-gray-500">Odds</span>
          <p className={`font-mono font-medium ${market.current_odds >= 0.5 ? 'text-green-400' : 'text-red-400'}`}>{formatOdds(market.current_odds)}</p>
        </div>
        <div>
          <span className="text-gray-500">Volume</span>
          <p className="font-mono text-white">{formatVolume(market.volume)}</p>
        </div>
        <div>
          <span className="text-gray-500">Close</span>
          <p className="text-gray-400">{market.close_time ? formatTime(market.close_time) : '-'}</p>
        </div>
      </div>
    </div>
  )
}
