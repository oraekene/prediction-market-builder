import { useState, useMemo } from 'react'
import { useMarkets } from '@/hooks/useMarkets'
import { formatOdds, formatVolume, formatTime } from '@/lib/utils'
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@/components/ui/Table'
import MarketSearch from './MarketSearch'

const CATEGORIES = ['All', 'Politics', 'Economy', 'Crypto', 'Sports', 'Science']

interface MarketItem {
  platform: string
  platform_market_id: string
  title: string
  category?: string | null
  current_odds: number
  volume: number
  close_time?: string | null
}

export default function MarketTable() {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState('All')
  const { data, isLoading, error } = useMarkets()

  if (isLoading) return <div className="text-gray-400">Loading markets...</div>
  if (error) return <div className="text-red-400">Error loading markets</div>

  const filteredMarkets = useMemo(() => {
    const markets = data?.markets ?? []
    return markets.filter((m: MarketItem) => {
      const matchesSearch = !searchQuery || m.title?.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesCategory = activeCategory === 'All' || m.category === activeCategory
      return matchesSearch && matchesCategory
    })
  }, [data, searchQuery, activeCategory])

  const totalVolume = useMemo(
    () => filteredMarkets.reduce((sum: number, m: MarketItem) => sum + (m.volume || 0), 0),
    [filteredMarkets],
  )

  const avgOdds = useMemo(
    () => filteredMarkets.length > 0
      ? filteredMarkets.reduce((sum: number, m: MarketItem) => sum + m.current_odds, 0) / filteredMarkets.length
      : 0,
    [filteredMarkets],
  )

  return (
    <div>
      {/* Quick stats */}
      <div className="mb-4 grid grid-cols-3 gap-4">
        <div className="rounded-lg border border-gray-800 bg-gray-950 p-3">
          <p className="text-xs text-gray-500">Total Markets</p>
          <p className="text-xl font-bold text-white">{filteredMarkets.length}</p>
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-950 p-3">
          <p className="text-xs text-gray-500">Avg Odds</p>
          <p className="text-xl font-bold text-white">{formatOdds(avgOdds)}</p>
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-950 p-3">
          <p className="text-xs text-gray-500">Total Volume</p>
          <p className="text-xl font-bold text-white">{formatVolume(totalVolume)}</p>
        </div>
      </div>

      {/* Search + filters */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-1">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                activeCategory === cat
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        <MarketSearch onSearch={setSearchQuery} />
      </div>

      {/* Table */}
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
            {filteredMarkets.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-12 text-center text-gray-500">
                  <p className="text-base">No markets found</p>
                  <p className="mt-1 text-sm">Try a different search or category</p>
                </TableCell>
              </TableRow>
            ) : (
              filteredMarkets.map((market: MarketItem) => (
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
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
