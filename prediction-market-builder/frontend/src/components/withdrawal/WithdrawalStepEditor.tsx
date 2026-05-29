import { WithdrawalStep } from '@/types/withdrawal'

interface Props {
  step: WithdrawalStep
  index: number
  onChange: (index: number, step: WithdrawalStep) => void
  onRemove: (index: number) => void
}

const CONDITION_TYPES = [
  { value: 'profit_threshold', label: 'Profit Threshold' },
  { value: 'profit_pct', label: 'Profit %' },
  { value: 'trailing_stop_fall', label: 'Trailing Stop Fall' },
  { value: 'profit_rise', label: 'Profit Rise' },
  { value: 'drawdown_from_peak', label: 'Drawdown from Peak' },
  { value: 'volatility_spike', label: 'Volatility Spike' },
] as const

const ACTION_TYPES = [
  { value: 'withdraw_pct', label: 'Withdraw %' },
  { value: 'withdraw_fixed', label: 'Withdraw Fixed Amount' },
  { value: 'convert_to_stablecoin', label: 'Convert to Stablecoin' },
] as const

const STABLECOINS = ['USDC', 'USDT', 'DAI']

export default function WithdrawalStepEditor({ step, index, onChange, onRemove }: Props) {
  const updateCondition = (field: string, value: string | number) => {
    onChange(index, {
      ...step,
      condition: { ...step.condition, [field]: value },
    })
  }

  const updateAction = (field: string, value: string | number) => {
    onChange(index, {
      ...step,
      action: { ...step.action, [field]: value },
    })
  }

  const updateStep = (field: string, value: boolean | number | undefined) => {
    onChange(index, { ...step, [field]: value })
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-400">Step {index + 1}</span>
        <button
          onClick={() => onRemove(index)}
          className="text-red-400 hover:text-red-300 text-sm transition-colors"
        >
          Remove
        </button>
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-1.5">Condition Type</label>
        <select
          value={step.condition.type}
          onChange={(e) => {
            const newCondition: WithdrawalStep['condition'] = { type: e.target.value }
            onChange(index, { ...step, condition: newCondition })
          }}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
        >
          {CONDITION_TYPES.map((ct) => (
            <option key={ct.value} value={ct.value}>
              {ct.label}
            </option>
          ))}
        </select>
      </div>

      {(step.condition.type === 'profit_threshold' || step.condition.type === 'profit_rise') && (
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Profit Amount ($)</label>
          <input
            type="number"
            value={step.condition.amount ?? ''}
            onChange={(e) => updateCondition('amount', parseFloat(e.target.value) || 0)}
            placeholder="0.00"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
          />
        </div>
      )}

      {(step.condition.type === 'profit_pct' || step.condition.type === 'trailing_stop_fall') && (
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Percentage (%)</label>
          <input
            type="number"
            value={step.condition.pct ?? ''}
            onChange={(e) => updateCondition('pct', parseFloat(e.target.value) || 0)}
            placeholder="0"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
          />
        </div>
      )}

      {(step.condition.type === 'drawdown_from_peak' || step.condition.type === 'volatility_spike') && (
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Threshold</label>
          <input
            type="number"
            value={step.condition.threshold ?? ''}
            onChange={(e) => updateCondition('threshold', parseFloat(e.target.value) || 0)}
            placeholder="0"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
          />
        </div>
      )}

      <div className="border-t border-gray-800 pt-4">
        <label className="block text-sm text-gray-400 mb-1.5">Action Type</label>
        <select
          value={step.action.type}
          onChange={(e) => {
            const newAction: WithdrawalStep['action'] = { type: e.target.value }
            onChange(index, { ...step, action: newAction })
          }}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
        >
          {ACTION_TYPES.map((at) => (
            <option key={at.value} value={at.value}>
              {at.label}
            </option>
          ))}
        </select>
      </div>

      {step.action.type === 'withdraw_pct' && (
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Withdraw Percentage (%)</label>
          <input
            type="number"
            value={step.action.pct ?? ''}
            onChange={(e) => updateAction('pct', parseFloat(e.target.value) || 0)}
            placeholder="0"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
          />
        </div>
      )}

      {step.action.type === 'withdraw_fixed' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Amount ($)</label>
            <input
              type="number"
              value={step.action.amount ?? ''}
              onChange={(e) => updateAction('amount', parseFloat(e.target.value) || 0)}
              placeholder="0.00"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Currency</label>
            <select
              value={step.action.currency ?? 'USD'}
              onChange={(e) => updateAction('currency', e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
            >
              <option value="USD">USD</option>
              <option value="USDC">USDC</option>
              <option value="USDT">USDT</option>
              <option value="DAI">DAI</option>
            </select>
          </div>
        </div>
      )}

      {step.action.type === 'convert_to_stablecoin' && (
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Target Stablecoin</label>
          <select
            value={step.action.stablecoin ?? 'USDC'}
            onChange={(e) => updateAction('stablecoin', e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
          >
            {STABLECOINS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="border-t border-gray-800 pt-4 flex flex-wrap gap-4 items-center">
        <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={step.once ?? false}
            onChange={(e) => updateStep('once', e.target.checked)}
            className="rounded border-gray-600 bg-gray-800 text-emerald-500 focus:ring-emerald-500"
          />
          Execute once
        </label>

        <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={step.sequential ?? false}
            onChange={(e) => updateStep('sequential', e.target.checked)}
            className="rounded border-gray-600 bg-gray-800 text-emerald-500 focus:ring-emerald-500"
          />
          Sequential
        </label>

        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">Cooldown (sec)</label>
          <input
            type="number"
            value={step.cooldown_seconds ?? ''}
            onChange={(e) => updateStep('cooldown_seconds', parseInt(e.target.value) || undefined)}
            placeholder="0"
            min="0"
            className="w-24 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>
    </div>
  )
}
