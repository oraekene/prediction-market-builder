import { useRiskSummary } from '@/hooks/useRisk'

export default function RiskMetricsCards() {
  const { data, isLoading } = useRiskSummary()

  if (isLoading) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <p className="text-sm text-gray-400">Loading...</p>
          </div>
        ))}
      </div>
    )
  }

  const cards = [
    { label: 'VaR (95%)', value: data?.var_95 != null ? `${(data.var_95 * 100).toFixed(2)}%` : '—', color: data?.var_95 && data.var_95 > 0.05 ? 'text-red-400' : 'text-yellow-400' },
    { label: 'Expected Shortfall', value: data?.es_95 != null ? `${(data.es_95 * 100).toFixed(2)}%` : '—', color: 'text-red-400' },
    { label: 'Drawdown', value: data?.current_drawdown != null ? `${(data.current_drawdown * 100).toFixed(2)}%` : '—', color: data?.current_drawdown && data.current_drawdown > 0.1 ? 'text-red-400' : 'text-yellow-400' },
    { label: 'Portfolio Vol', value: data?.portfolio_volatility != null ? `${(data.portfolio_volatility * 100).toFixed(2)}%` : '—', color: 'text-blue-400' },
  ]

  return (
    <div className="grid grid-cols-4 gap-4">
      {cards.map((card) => (
        <div key={card.label} className="rounded-lg border border-gray-700 bg-gray-900 p-4">
          <p className="text-sm text-gray-400">{card.label}</p>
          <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
        </div>
      ))}
    </div>
  )
}
