import { useMarkets } from '@/hooks/useMarkets'
import { formatOdds, formatVolume, formatTime } from '@/lib/utils'
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@/components/ui/Table'
import MarketSearch from './MarketSearch'

export default function MarketTable() {
  const { data, isLoading, error } = useMarkets()

  if (isLoading) return <div className="text-gray-400">Loading markets...</div>
  if (error) return <div className="text-red-400">Error loading markets</div>

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Markets</h1>
        <MarketSearch />
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-800">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader>Market</TableHeader>
              <TableHeader>Platform</TableHeader>
              <TableHeader>Odds</TableHeader>
              <TableHeader>Volume</TableHeader>
              <TableHeader>Close</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {data?.markets.map((market: any) => (
              <TableRow key={`${market.platform}-${market.platform_market_id}`}>
                <TableCell>
                  <div className="font-medium text-white">{market.title}</div>
                  {market.category && <div className="text-xs text-gray-500">{market.category}</div>}
                </TableCell>
                <TableCell>
                  <span className="rounded-full bg-gray-800 px-2 py-0.5 text-xs capitalize">{market.platform}</span>
                </TableCell>
                <TableCell className={`font-mono font-medium ${market.current_odds >= 0.5 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatOdds(market.current_odds)}
                </TableCell>
                <TableCell className="font-mono text-gray-300">{formatVolume(market.volume)}</TableCell>
                <TableCell className="text-gray-400">{market.close_time ? formatTime(market.close_time) : '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
