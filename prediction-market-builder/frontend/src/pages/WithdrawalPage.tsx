import { useState, useEffect } from 'react'
import {
  useSafeWallets,
  useWithdrawalStrategies,
  useCreateWithdrawalStrategy,
  useUpdateWithdrawalStrategy,
  useDeleteWithdrawalStrategy,
  useEvaluateWithdrawalStrategy,
} from '@/hooks/useWithdrawal'
import WithdrawalStepEditor from '@/components/withdrawal/WithdrawalStepEditor'
import { WithdrawalStep, WithdrawalStrategy } from '@/types/withdrawal'

let stepIdCounter = 0
function generateStepId() {
  return `step-${Date.now()}-${++stepIdCounter}`
}

function makeEmptyStep(): WithdrawalStep {
  return {
    id: generateStepId(),
    condition: { type: 'profit_pct', pct: 20 },
    action: { type: 'withdraw_pct', pct: 50 },
    once: false,
    cooldown_seconds: 0,
    sequential: false,
  }
}

export default function WithdrawalPage() {
  const { data: strategies = [], isLoading: strategiesLoading } = useWithdrawalStrategies()
  const { data: wallets = [] } = useSafeWallets()
  const createStrategy = useCreateWithdrawalStrategy()
  const updateStrategy = useUpdateWithdrawalStrategy()
  const deleteStrategy = useDeleteWithdrawalStrategy()
  const evaluateStrategy = useEvaluateWithdrawalStrategy()

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [strategyName, setStrategyName] = useState('')
  const [strategyDescription, setStrategyDescription] = useState('')
  const [isActive, setIsActive] = useState(false)
  const [safeWalletId, setSafeWalletId] = useState<string>('')
  const [steps, setSteps] = useState<WithdrawalStep[]>([makeEmptyStep()])
  const [testResult, setTestResult] = useState<{ triggered: boolean; steps_evaluated: number } | null>(null)

  const selectedStrategy = strategies.find((s) => s.id === selectedId)

  useEffect(() => {
    if (selectedStrategy) {
      setStrategyName(selectedStrategy.name)
      setStrategyDescription(selectedStrategy.description ?? '')
      setIsActive(selectedStrategy.is_active)
      setSafeWalletId(selectedStrategy.safe_wallet_id ?? '')
      setSteps(selectedStrategy.steps.length > 0 ? selectedStrategy.steps : [makeEmptyStep()])
      setTestResult(null)
    }
  }, [selectedId, selectedStrategy])

  const handleNew = () => {
    setSelectedId(null)
    setStrategyName('')
    setStrategyDescription('')
    setIsActive(false)
    setSafeWalletId('')
    setSteps([makeEmptyStep()])
    setTestResult(null)
  }

  const handleStepChange = (index: number, step: WithdrawalStep) => {
    setSteps((prev) => prev.map((s, i) => (i === index ? step : s)))
  }

  const handleRemoveStep = (index: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== index))
  }

  const handleAddStep = () => {
    setSteps((prev) => [...prev, makeEmptyStep()])
  }

  const handleSave = async () => {
    if (!strategyName.trim()) return

    if (selectedId) {
      await updateStrategy.mutateAsync({
        id: selectedId,
        data: {
          name: strategyName,
          description: strategyDescription || undefined,
          is_active: isActive,
          safe_wallet_id: safeWalletId || undefined,
          steps,
        },
      })
    } else {
      const created = await createStrategy.mutateAsync({
        name: strategyName,
        description: strategyDescription || undefined,
        safe_wallet_id: safeWalletId || undefined,
        steps,
      })
      setSelectedId(created.id)
    }
  }

  const handleTest = async () => {
    if (!selectedId) return
    setTestResult(null)
    const result = await evaluateStrategy.mutateAsync(selectedId)
    setTestResult(result)
  }

  const handleDelete = async () => {
    if (!selectedId) return
    await deleteStrategy.mutateAsync(selectedId)
    handleNew()
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Withdrawal Strategy Builder</h1>
          <button
            onClick={handleNew}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
          >
            + New Strategy
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-1 space-y-2">
            <p className="text-sm text-gray-400 uppercase tracking-wide mb-2">Strategies</p>
            {strategiesLoading ? (
              <p className="text-gray-500 text-sm">Loading...</p>
            ) : strategies.length === 0 ? (
              <p className="text-gray-500 text-sm">No strategies yet.</p>
            ) : (
              strategies.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedId(s.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    selectedId === s.id
                      ? 'bg-emerald-900/40 border border-emerald-700 text-emerald-300'
                      : 'bg-gray-900 border border-gray-800 text-gray-300 hover:border-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="truncate">{s.name}</span>
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ml-2 ${
                        s.is_active ? 'bg-emerald-400' : 'bg-gray-600'
                      }`}
                    />
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="lg:col-span-3 space-y-5">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Strategy Name</label>
                  <input
                    type="text"
                    value={strategyName}
                    onChange={(e) => setStrategyName(e.target.value)}
                    placeholder="e.g. DCA Profit Protection"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Safe Wallet</label>
                  <select
                    value={safeWalletId}
                    onChange={(e) => setSafeWalletId(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                  >
                    <option value="">Select wallet...</option>
                    {wallets.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name} ({w.currency})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Description</label>
                <input
                  type="text"
                  value={strategyDescription}
                  onChange={(e) => setStrategyDescription(e.target.value)}
                  placeholder="Optional description"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
                />
              </div>

              <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-800 text-emerald-500 focus:ring-emerald-500"
                />
                Active
              </label>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm text-gray-400 uppercase tracking-wide">Steps</h2>
                <button
                  onClick={handleAddStep}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs font-medium transition-colors"
                >
                  + Add Step
                </button>
              </div>

              {steps.map((step, i) => (
                <WithdrawalStepEditor
                  key={step.id}
                  step={step}
                  index={i}
                  onChange={handleStepChange}
                  onRemove={handleRemoveStep}
                />
              ))}
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handleSave}
                disabled={!strategyName.trim() || createStrategy.isPending || updateStrategy.isPending}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {createStrategy.isPending || updateStrategy.isPending ? 'Saving...' : 'Save Strategy'}
              </button>

              {selectedId && (
                <>
                  <button
                    onClick={handleTest}
                    disabled={evaluateStrategy.isPending}
                    className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    {evaluateStrategy.isPending ? 'Testing...' : 'Test Strategy'}
                  </button>
                  <button
                    onClick={handleDelete}
                    disabled={deleteStrategy.isPending}
                    className="px-5 py-2.5 bg-red-900/50 hover:bg-red-900 text-red-400 rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    Delete
                  </button>
                </>
              )}
            </div>

            {testResult && (
              <div
                className={`p-4 rounded-xl border text-sm ${
                  testResult.triggered
                    ? 'bg-emerald-900/20 border-emerald-700 text-emerald-300'
                    : 'bg-gray-900 border-gray-800 text-gray-400'
                }`}
              >
                {testResult.triggered
                  ? `Strategy triggered! Evaluated ${testResult.steps_evaluated} step(s).`
                  : `No triggers fired. Evaluated ${testResult.steps_evaluated} step(s).`}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
