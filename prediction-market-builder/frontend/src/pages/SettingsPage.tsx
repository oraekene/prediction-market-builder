import { useState, type FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/auth'
import { useAuth } from '@/contexts/AuthContext'

function fetchSettings() {
  return apiFetch('/api/paper/connection-test').then(r => r.ok ? r.json() : null)
}

async function updateTradingMode(mode: 'paper' | 'live') {
  const res = await apiFetch('/api/paper/confirm-live', {
    method: 'POST',
    body: JSON.stringify({ mode }),
  })
  if (!res.ok) throw new Error('Failed to update trading mode')
  return res.json()
}

export default function SettingsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [polymarketKey, setPolymarketKey] = useState('')
  const [kalshiKey, setKalshiKey] = useState('')
  const [maxLoss, setMaxLoss] = useState('100')
  const [showKeys, setShowKeys] = useState(false)
  const [saved, setSaved] = useState(false)

  const { data: health } = useQuery({
    queryKey: ['settings-health'],
    queryFn: fetchSettings,
    refetchInterval: 60_000,
  })

  const modeMutation = useMutation({
    mutationFn: updateTradingMode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings-health'] })
    },
  })

  function handleSaveKeys(e: FormEvent) {
    e.preventDefault()
    localStorage.setItem('pm_polymarket_key', polymarketKey)
    localStorage.setItem('pm_kalshi_key', kalshiKey)
    localStorage.setItem('pm_max_loss', maxLoss)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const isConnected = health !== null && health !== undefined

  return (
    <div className="space-y-8">
      <h1 className="text-xl font-semibold">Settings</h1>

      {/* Profile */}
      <section className="rounded-lg border border-gray-800 bg-gray-950 p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">Profile</h2>
        <div className="space-y-2 text-sm">
          <p><span className="text-gray-500">Email:</span> <span className="text-white">{user?.email}</span></p>
          {user?.display_name && (
            <p><span className="text-gray-500">Display Name:</span> <span className="text-white">{user.display_name}</span></p>
          )}
        </div>
      </section>

      {/* API Keys */}
      <section className="rounded-lg border border-gray-800 bg-gray-950 p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">Exchange API Keys</h2>
        <p className="mb-4 text-xs text-gray-500">
          Keys are stored locally and sent per-session. Never share your private keys.
        </p>
        <form onSubmit={handleSaveKeys} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-gray-400">Polymarket API Key</label>
            <input
              type={showKeys ? 'text' : 'password'}
              value={polymarketKey}
              onChange={e => setPolymarketKey(e.target.value)}
              placeholder="Enter your Polymarket API key"
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-400">Kalshi API Key</label>
            <input
              type={showKeys ? 'text' : 'password'}
              value={kalshiKey}
              onChange={e => setKalshiKey(e.target.value)}
              placeholder="Enter your Kalshi API key"
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs text-gray-400">
              <input type="checkbox" checked={showKeys} onChange={e => setShowKeys(e.target.checked)} />
              Show keys
            </label>
            <button
              type="submit"
              className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700"
            >
              {saved ? 'Saved' : 'Save Keys'}
            </button>
          </div>
        </form>
      </section>

      {/* Trading Mode */}
      <section className="rounded-lg border border-gray-800 bg-gray-950 p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">Trading Mode</h2>
        <div className="flex items-center gap-4">
          <button
            onClick={() => modeMutation.mutate('paper')}
            className={`rounded px-4 py-2 text-sm font-medium transition-colors ${
              !isConnected
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-800 text-gray-400'
            }`}
          >
            Paper Trading
          </button>
          <button
            onClick={() => modeMutation.mutate('live')}
            className={`rounded px-4 py-2 text-sm font-medium transition-colors ${
              isConnected
                ? 'bg-green-700 text-white hover:bg-green-800'
                : 'bg-gray-800 text-gray-400'
            }`}
          >
            Live Trading
          </button>
          <span className="ml-2 text-xs text-gray-500">
            Current: <span className={isConnected ? 'text-green-400' : 'text-yellow-400'}>
              {isConnected ? 'Ready for live' : 'Paper mode'}
            </span>
          </span>
        </div>
      </section>

      {/* Safety Limits */}
      <section className="rounded-lg border border-gray-800 bg-gray-950 p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">Safety Limits</h2>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-gray-400">Max Session Loss ($)</label>
            <input
              type="number"
              value={maxLoss}
              onChange={e => setMaxLoss(e.target.value)}
              min={10}
              max={10000}
              className="w-40 rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
            />
            <p className="mt-1 text-xs text-gray-600">Auto kill-switch triggers when losses exceed this amount in a session</p>
          </div>
        </div>
      </section>

      {/* Connection Status */}
      <section className="rounded-lg border border-gray-800 bg-gray-950 p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-400">Connection Status</h2>
        <div className="space-y-1 text-xs">
          <p><span className="text-gray-500">Backend:</span> <span className="text-green-400">Online</span></p>
          <p><span className="text-gray-500">Exchange connections:</span> <span className={isConnected ? 'text-green-400' : 'text-gray-500'}>
            {isConnected ? 'Verified' : 'Not configured'}
          </span></p>
        </div>
      </section>
    </div>
  )
}
