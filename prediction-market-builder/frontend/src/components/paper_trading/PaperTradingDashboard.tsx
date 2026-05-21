import PaperWalletCard from './PaperWalletCard'
import PaperOrderForm from './PaperOrderForm'
import PaperOrderList from './PaperOrderList'
import PaperPerformanceChart from './PaperPerformanceChart'
import StrategyComparison from './StrategyComparison'
import { useState } from 'react'

type Tab = 'overview' | 'trade' | 'orders' | 'compare'

export default function PaperTradingDashboard() {
  const [tab, setTab] = useState<Tab>('overview')

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'trade', label: 'Place Trade' },
    { key: 'orders', label: 'Orders' },
    { key: 'compare', label: 'Compare' },
  ]

  return (
    <div className="space-y-4">
      <PaperWalletCard />

      <div className="flex gap-1 border-b border-gray-800 pb-0">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={ounded-t-md px-4 py-2 text-sm font-medium transition-colors }
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="pt-2">
        {tab === 'overview' && (
          <div className="space-y-4">
            <PaperPerformanceChart />
            <PaperOrderList />
          </div>
        )}
        {tab === 'trade' && <PaperOrderForm />}
        {tab === 'orders' && <PaperOrderList />}
        {tab === 'compare' && <StrategyComparison />}
      </div>
    </div>
  )
}
