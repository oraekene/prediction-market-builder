import { formatOdds, formatVolume, formatTime } from '@/lib/utils'

interface MarketRowProps {
  market: {
    title: string
    category?: string
    platform: string
    current_odds: number
    volume: number
    close_time?: string
    platform_market_id: string
  }
}

export default function MarketRow({ market }: MarketRowProps) {
  return (
    <tr className="border-b border-gray-800 hover:bg-gray-800/50">
      <td className="px-4 py-3">
        <div className="font-medium text-white">{market.title}</div>
        {market.category && <div className="text-xs text-gray-500">{market.category}</div>}
      </td>
      <td className="px-4 py-3">
        <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs capitalize">{market.platform}</span>
      </td>
      <td className={`px-4 py-3 font-mono font-medium ${market.current_odds >= 0.5 ? 'text-green-400' : 'text-red-400'}`}>
        {formatOdds(market.current_odds)}
      </td>
      <td className="px-4 py-3 font-mono text-gray-300">{formatVolume(market.volume)}</td>
      <td className="px-4 py-3 text-gray-400">{market.close_time ? formatTime(market.close_time) : '-'}</td>
    </tr>
  )
}
