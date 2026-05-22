interface MarketSearchProps {
  onSearch?: (query: string) => void
}

export default function MarketSearch({ onSearch }: MarketSearchProps) {
  return (
    <input
      type="text"
      placeholder="Search markets..."
      onChange={(e) => onSearch?.(e.target.value)}
      className="w-64 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
    />
  )
}
