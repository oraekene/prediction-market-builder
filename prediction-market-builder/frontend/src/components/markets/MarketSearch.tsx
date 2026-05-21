import { useState } from 'react'

export default function MarketSearch() {
  const [query, setQuery] = useState('')
  return (
    <input
      type="text"
      placeholder="Search markets..."
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      className="w-64 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
    />
  )
}
