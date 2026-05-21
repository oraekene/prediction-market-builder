import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'

const navItems = [
  { path: '/markets', label: 'Markets' },
  { path: '/strategies', label: 'Strategies' },
  { path: '/analytics', label: 'Analytics' },
  { path: '/research', label: 'Research' },
  { path: '/settings', label: 'Settings' },
]

export default function Header() {
  const location = useLocation()
  return (
    <header className="border-b border-gray-800 bg-gray-950 px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-8">
          <span className="text-lg font-bold text-white">PM Builder</span>
          <nav className="flex gap-1">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm transition-colors',
                  location.pathname.startsWith(item.path)
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-400 hover:text-white'
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">Connected</span>
        </div>
      </div>
    </header>
  )
}
