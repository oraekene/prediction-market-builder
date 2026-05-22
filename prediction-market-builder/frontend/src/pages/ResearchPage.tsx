import { useState, useEffect, useMemo } from 'react'
import {
  fetchResearchSessions,
  fetchResearchStats,
  fetchResearchResults,
  fetchResearchConfig,
  triggerResearchRun,
  triggerContinuousResearch,
  stopResearch,
  fetchClimate,
  fetchAlphaVectors,
  triggerRlmScan,
} from '@/lib/api'
import { useResearchWebSocket } from '@/hooks/useResearchWebSocket'
import { cn } from '@/lib/utils'
import { IterationChart } from '@/components/research/IterationChart'

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function ResearchPage() {
  const [sessions, setSessions] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [results, setResults] = useState<any[]>([])
  const [, setConfig] = useState<any>(null)
  const [climate, setClimate] = useState<any>(null)
  const [features, setFeatures] = useState<Record<string, number> | null>(null)
  const [alphaVectors, setAlphaVectors] = useState<any[]>([])
  const [activeIteration, setActiveIteration] = useState<any>(null)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [s, st, cfg, cl, av] = await Promise.all([
        fetchResearchSessions(),
        fetchResearchStats(),
        fetchResearchConfig(),
        fetchClimate(),
        fetchAlphaVectors(5),
      ])
      setSessions(s.sessions)
      setStats(st)
      setConfig(cfg)
      setClimate(cl)
      setFeatures(null)
      setAlphaVectors(av.vectors || [])
    } catch { /* ignore */ }
  }

  const wsHandlers: Record<string, (data: any) => void> = useMemo(() => ({
    iteration_complete(_data: any) {
      setActiveIteration(null)
      setRunning(false)
      loadData()
      if (selectedSession) {
        fetchResearchResults(selectedSession, 20).then(r => setResults(r.results)).catch(() => {})
      }
    },
    hypothesis(data: any) {
      setActiveIteration((prev: any) => ({ ...prev, hypothesis: data.hypothesis, ...data }))
    },
    tabpfn_result(data: any) {
      setActiveIteration((prev: any) => ({ ...prev, tabpfn: data }))
    },
    backtest_progress(data: any) {
      setActiveIteration((prev: any) => ({ ...prev, progress: data.percent }))
    },
    session_summary() {
      loadData()
    },
    error(data: any) {
      console.error('Research WS error:', data.message)
    },
  }), [selectedSession])

  useResearchWebSocket(running ? selectedSession : null, wsHandlers)

  async function handleRunOnce() {
    try {
      setRunning(true)
      const result = await triggerResearchRun()
      setSelectedSession(result.session_id)
    } catch { setRunning(false) }
  }

  async function handleRunContinuous() {
    try {
      setRunning(true)
      const result = await triggerContinuousResearch()
      setSelectedSession(result.session_id)
    } catch { setRunning(false) }
  }

  async function handleStop() {
    if (!selectedSession) return
    try {
      await stopResearch(selectedSession)
      setRunning(false)
      loadData()
    } catch { /* ignore */ }
  }

  async function handleRlmScan() {
    try {
      await triggerRlmScan('forum')
      loadData()
    } catch { /* ignore */ }
  }

  async function selectSession(id: string) {
    setSelectedSession(id)
    try {
      const r = await fetchResearchResults(id, 50)
      setResults(r.results)
    } catch { /* ignore */ }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">pi-autoresearch</h1>
        <div className="flex gap-2">
          <button
            onClick={handleRunOnce}
            disabled={running}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {running ? 'Running...' : 'Run Now'}
          </button>
          <button
            onClick={handleRunContinuous}
            disabled={running}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            Continuous
          </button>
          <button
            onClick={handleStop}
            disabled={!running}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            Stop
          </button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-5 gap-4">
          <StatCard label="Total Sessions" value={stats.total_sessions} />
          <StatCard label="Kept" value={stats.total_kept} color="text-green-400" />
          <StatCard label="Avg Sharpe" value={stats.avg_sharpe.toFixed(2)} color="text-blue-400" />
          <StatCard label="Keep Rate" value={`${(stats.keep_rate * 100).toFixed(0)}%`} color="text-green-400" />
          <StatCard label="Best Sharpe" value={stats.best_sharpe.toFixed(2)} color="text-yellow-400" />
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-4">
          <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-300">Active Session</h2>
            {activeIteration ? (
              <div className="space-y-3">
                <div>
                  <span className="text-xs text-gray-500">Hypothesis:</span>
                  <p className="font-mono text-sm text-white">{activeIteration.hypothesis || 'generating...'}</p>
                </div>
                {activeIteration.progress !== undefined && (
                  <div>
                    <div className="mb-1 flex justify-between text-xs text-gray-500">
                      <span>Backtest</span>
                      <span>{activeIteration.progress}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-gray-800">
                      <div
                        className="h-2 rounded-full bg-blue-500 transition-all"
                        style={{ width: `${activeIteration.progress}%` }}
                      />
                    </div>
                  </div>
                )}
                {activeIteration.tabpfn && (
                  <div className="flex gap-4 text-sm">
                    <span className="text-gray-500">
                      TabPFN: <span className="text-white">{activeIteration.tabpfn.probability}</span>
                    </span>
                    <span className="text-gray-500">
                      Confidence: <span className="text-white">{activeIteration.tabpfn.confidence}</span>
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No active iteration</p>
            )}
          </div>

          <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-300">Iteration History</h2>
            {results.length === 0 ? (
              <p className="text-sm text-gray-500">No results yet</p>
            ) : (
              <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-left text-xs uppercase text-gray-500">
                      <th className="px-3 py-2 font-medium">#</th>
                      <th className="px-3 py-2 font-medium">Hypothesis</th>
                      <th className="px-3 py-2 font-medium">Regime</th>
                      <th className="px-3 py-2 font-medium">Score</th>
                      <th className="px-3 py-2 font-medium">Sharpe</th>
                      <th className="px-3 py-2 font-medium">Win Rate</th>
                      <th className="px-3 py-2 font-medium">TabPFN</th>
                      <th className="px-3 py-2 font-medium">Verdict</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.slice().reverse().map((r) => (
                      <tr key={r.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                        <td className="px-3 py-2 text-gray-400">{r.iteration}</td>
                        <td className="max-w-[200px] truncate px-3 py-2 text-white">{r.hypothesis}</td>
                        <td className="px-3 py-2 text-gray-400">{r.regime_at_time || '-'}</td>
                        <td className="px-3 py-2 font-mono text-white">{r.composite_score.toFixed(3)}</td>
                        <td className="px-3 py-2 font-mono text-blue-400">{r.backtest_sharpe.toFixed(3)}</td>
                        <td className="px-3 py-2 font-mono">{(r.backtest_win_rate * 100).toFixed(0)}%</td>
                        <td className="px-3 py-2 font-mono">{(r.tabpfn_probability * 100).toFixed(0)}%</td>
                        <td className="px-3 py-2">
                          <VerdictBadge verdict={r.verdict} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4">
                <IterationChart results={results} />
              </div>
              </>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-300">Sessions</h2>
            {sessions.length === 0 ? (
              <p className="text-sm text-gray-500">No sessions</p>
            ) : (
              <div className="space-y-2">
                {sessions.slice(0, 10).map((s) => (
                  <button
                    key={s.id}
                    onClick={() => selectSession(s.id)}
                    className={cn(
                      'w-full rounded-md border p-3 text-left text-sm transition-colors',
                      selectedSession === s.id
                        ? 'border-blue-600 bg-blue-900/20'
                        : 'border-gray-800 hover:border-gray-700',
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-white">{s.mode}</span>
                      <SessionStatusBadge status={s.status} />
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {s.current_iteration} iterations · Sharpe {s.avg_sharpe.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-500">{formatTime(s.created_at)}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-300">Climate & Features</h2>
            {climate ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Regime</span>
                  <span className="text-white">{climate.regime || '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Volatility</span>
                  <span className="font-mono text-white">{climate.metrics?.volatility?.toFixed(4) || '-'}</span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-500">Not available</p>
            )}
            {features && Object.keys(features).length > 0 && (
              <div className="mt-3 space-y-1">
                <span className="text-xs font-semibold text-gray-500">Top Features</span>
                {Object.entries(features).slice(0, 3).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-gray-400">{k}</span>
                    <span className="text-white">{typeof v === 'number' ? v.toFixed(3) : v}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-300">RLM Alpha Vectors</h2>
              <button
                onClick={handleRlmScan}
                className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-400 hover:text-white"
              >
                Scan
              </button>
            </div>
            {alphaVectors.length === 0 ? (
              <p className="mt-2 text-xs text-gray-500">No vectors</p>
            ) : (
              <div className="mt-2 space-y-2">
                {alphaVectors.map((v) => (
                  <div key={v.id} className="rounded bg-gray-900 p-2 text-xs">
                    <div className="text-gray-400">{v.source_type}</div>
                    <div className="text-gray-500">{v.token_count} tokens</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-950 p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={cn('mt-1 text-2xl font-bold', color || 'text-white')}>{value}</div>
    </div>
  )
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const colors: Record<string, string> = {
    KEPT: 'bg-green-900 text-green-400',
    WARN: 'bg-yellow-900 text-yellow-400',
    REVERTED: 'bg-red-900 text-red-400',
    SKIPPED: 'bg-gray-800 text-gray-400',
  }
  return (
    <span className={cn('rounded px-2 py-0.5 text-xs font-medium', colors[verdict] || 'bg-gray-800 text-gray-400')}>
      {verdict}
    </span>
  )
}

function SessionStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: 'text-green-400',
    paused: 'text-yellow-400',
    completed: 'text-blue-400',
    failed: 'text-red-400',
  }
  return <span className={cn('text-xs font-medium', colors[status] || 'text-gray-400')}>{status}</span>
}
