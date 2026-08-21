import { useState } from 'react'

export default function Sidebar() {
  const [activeSection, setActiveSection] = useState('watchlist')
  return (
    <aside className="w-56 border-r border-gray-800 bg-gray-950 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Market Watch</h3>
      <div className="space-y-1">
        {['All Markets', 'Politics', 'Economy', 'Crypto', 'Sports', 'Watchlist'].map((item) => (
          <button
            key={item}
            onClick={() => setActiveSection(item.toLowerCase())}
            className={`w-full rounded-md px-3 py-1.5 text-left text-sm transition-colors ${
              activeSection === item.toLowerCase()
                ? 'bg-gray-800 text-white'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {item}
          </button>
        ))}
      </div>
    </aside>
  )
}
