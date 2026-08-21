import { useState, type FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '@/lib/auth'
import { useAuth } from '@/contexts/AuthContext'

async function fetchBackendHealth() {
  const res = await fetch('/health')
  if (!res.ok) return null
  return res.json()
}

async function fetchConnectionTest() {
  return apiFetch('/api/paper/connection-test').then(r => r.ok ? r.json() : null)
}

async function saveExchangeKeys(keys: Record<string, string>) {
  const res = await apiFetch('/api/auth/keys', {
    method: 'PUT',
    body: JSON.stringify(keys),
  })
  if (!res.ok) throw new Error('Failed to save keys')
  return res.json()
}

async function setTradingMode(mode: 'paper' | 'live') {
  const res = await apiFetch('/api/paper/trading-mode', {
    method: 'POST',
    body: JSON.stringify({ mode }),
  })
  if (!res.ok) throw new Error('Failed to update trading mode')
  return res.json()
}

async function confirmLive() {
  const res = await apiFetch('/api/paper/confirm-live', { method: 'POST' })
  if (!res.ok) throw new Error('Failed to confirm live trading')
  return res.json()
}

export default function SettingsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [polymarketKey, setPolymarketKey] = useState('')
  const [kalshiKey, setKalshiKey] = useState('')
  const [driftKey, setDriftKey] = useState('')
  const [maxLoss, setMaxLoss] = useState('100')
  const [showKeys, setShowKeys] = useState(false)
  const [saved, setSaved] = useState(false)
  const [tradingMode, setTradingModeState] = useState<'paper' | 'live'>('paper')

  const { data: health } = useQuery({
    queryKey: ['backend-health'],
    queryFn: fetchBackendHealth,
    refetchInterval: 60_000,
  })

  const { data: connection } = useQuery({
    queryKey: ['connection-test'],
    queryFn: fetchConnectionTest,
    refetchInterval: 60_000,
  })

  const keysMutation = useMutation({ mutationFn: saveExchangeKeys })

  const modeMutation = useMutation({
    mutationFn: async (mode: 'paper' | 'live') => {
      const result = await setTradingMode(mode)
      if (mode === 'live') {
        await confirmLive()
      }
      return result
    },
    onSuccess: (_data, mode) => {
      setTradingModeState(mode)
      queryClient.invalidateQueries({ queryKey: ['connection-test'] })
    },
  })

  function handleSaveKeys(e: FormEvent) {
    e.preventDefault()
    const keys: Record<string, string> = {}
    if (polymarketKey.trim()) keys.polymarket_key = polymarketKey.trim()
    if (kalshiKey.trim()) keys.kalshi_key = kalshiKey.trim()
    if (driftKey.trim()) keys.drift_key = driftKey.trim()
    if (Object.keys(keys).length === 0) {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      return
    }
    keysMutation.mutate(
      keys,
      {
        onSuccess: () => {
          setPolymarketKey('')
          setKalshiKey('')
          setDriftKey('')
          setSaved(true)
          setTimeout(() => setSaved(false), 2000)
        },
      },
    )
  }

  const backendOnline = health !== null && health !== undefined
  const connectionVerified = connection !== null && connection !== undefined

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
          Keys are encrypted at rest on the server and only decrypted when placing orders.
          Never share your private keys.
        </p>
        {keysMutation.isError && (
          <p className="mb-3 text-xs text-red-400">Failed to save keys. Please try again.</p>
        )}
        <form onSubmit={handleSaveKeys} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs text-gray-400">Polymarket API Key (api_key:secret)</label>
            <input
              type={showKeys ? 'text' : 'password'}
              value={polymarketKey}
              onChange={e => setPolymarketKey(e.target.value)}
              placeholder="Enter your Polymarket API key"
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-400">Kalshi Private Key</label>
            <input
              type={showKeys ? 'text' : 'password'}
              value={kalshiKey}
              onChange={e => setKalshiKey(e.target.value)}
              placeholder="Enter your Kalshi API key"
              className="w-full rounded border border-gray-700 bg-gray-900 px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-400">Drift API Key</label>
            <input
              type={showKeys ? 'text' : 'password'}
              value={driftKey}
              onChange={e => setDriftKey(e.target.value)}
              placeholder="Enter your Drift API key"
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
              disabled={keysMutation.isPending}
              className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {keysMutation.isPending ? 'Saving…' : saved ? 'Saved' : 'Save Keys'}
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
              tradingMode === 'paper'
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-800 text-gray-400'
            }`}
          >
            Paper Trading
          </button>
          <button
            onClick={() => modeMutation.mutate('live')}
            className={`rounded px-4 py-2 text-sm font-medium transition-colors ${
              tradingMode === 'live'
                ? 'bg-green-700 text-white hover:bg-green-800'
                : 'bg-gray-800 text-gray-400'
            }`}
          >
            Live Trading
          </button>
          {modeMutation.isError && (
            <span className="ml-2 text-xs text-red-400">
              {modeMutation.error instanceof Error ? modeMutation.error.message : 'Failed to update mode'}
            </span>
          )}
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
          <p>
            <span className="text-gray-500">Backend:</span>{' '}
            <span className={backendOnline ? 'text-green-400' : 'text-red-400'}>
              {backendOnline ? 'Online' : 'Offline'}
            </span>
          </p>
          <p>
            <span className="text-gray-500">Exchange connections:</span>{' '}
            <span className={connectionVerified ? 'text-green-400' : 'text-gray-500'}>
              {connectionVerified ? 'Verified' : 'Not configured'}
            </span>
          </p>
        </div>
      </section>
    </div>
  )
}
