import { useState, type FormEvent } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Navigate, useNavigate } from 'react-router-dom'

const features = [
  { icon: '📊', label: 'Multi-exchange markets', desc: 'Polymarket, Kalshi, Drift in one view' },
  { icon: '⚡', label: 'Smart strategy builder', desc: 'Visual node editor or natural language chat' },
  { icon: '🛡️', label: 'Risk-first design', desc: 'VaR, drawdown limits, auto-kill switch' },
  { icon: '🧠', label: 'AI research pipeline', desc: 'Auto-research, regime detection, SHAP explainability' },
  { icon: '🔁', label: 'Meta-strategies', desc: 'Let your best strategies compete automatically' },
  { icon: '🎮', label: 'Paper trading', desc: 'Practice risk-free before going live' },
]

export default function LoginPage() {
  const { user, login, register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [isRegister, setIsRegister] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/markets" replace />

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (isRegister) {
        await register(email, password, displayName || undefined)
      } else {
        await login(email, password)
      }
      navigate('/markets', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-gray-950">
      {/* Hero / Feature panel */}
      <div className="hidden w-1/2 flex-col justify-center px-16 lg:flex">
        <h1 className="text-4xl font-bold text-white">PM Builder</h1>
        <p className="mt-3 text-lg text-gray-400">
          Build, backtest, and execute prediction market strategies across multiple platforms.
        </p>
        <div className="mt-10 grid grid-cols-2 gap-4">
          {features.map((f) => (
            <div key={f.label} className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
              <span className="text-xl">{f.icon}</span>
              <h3 className="mt-2 text-sm font-semibold text-white">{f.label}</h3>
              <p className="mt-1 text-xs text-gray-500">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Auth form */}
      <div className="flex w-full items-center justify-center px-4 lg:w-1/2">
        <div className="w-full max-w-sm">
          <h1 className="mb-2 text-center text-2xl font-bold text-white lg:hidden">PM Builder</h1>
          <p className="mb-8 text-center text-lg text-gray-300 lg:hidden">Prediction Market Strategy Builder</p>

          <h2 className="mb-6 text-center text-xl font-semibold text-white">
            {isRegister ? 'Create Account' : 'Sign In'}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <input
                type="text"
                placeholder="Display name (optional)"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
            )}
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-2 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Please wait...' : isRegister ? 'Register' : 'Sign In'}
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-gray-500">
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              onClick={() => { setIsRegister(!isRegister); setError('') }}
              className="text-blue-400 hover:text-blue-300"
            >
              {isRegister ? 'Sign in' : 'Register'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
