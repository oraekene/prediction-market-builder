interface MarketDetailProps {
  marketId: string
}

export default function MarketDetail({ marketId }: MarketDetailProps) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
      <h2 className="text-sm font-semibold text-gray-400">Market Detail: {marketId}</h2>
      <p className="mt-2 text-gray-500">Full detail view coming in Phase 2.</p>
    </div>
  )
}
