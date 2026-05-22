import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'

const navItems = [
  { path: '/markets', label: 'Markets' },
  { path: '/strategies', label: 'Strategies' },
  { path: '/analytics', label: 'Analytics' },
  { path: '/research', label: 'Research' },
  { path: '/settings', label: 'Settings' },
  { path: '/paper-trading', label: 'Paper Trading' },
  { path: '/meta-strategies', label: 'Meta-Strategies' },
]

export default function Header() {
  const location = useLocation()
  const { user, logout } = useAuth()
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
          <span className="text-sm text-gray-400">{user?.email}</span>
          <button onClick={logout} className="rounded px-2 py-1 text-xs text-gray-500 hover:text-white">
            Logout
          </button>
        </div>
      </div>
    </header>
  )
}
