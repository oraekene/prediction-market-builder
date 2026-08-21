import RiskMetricsCards from './RiskMetricsCards'
import CorrelationMatrix from './CorrelationMatrix'
import DrawdownChart from './DrawdownChart'

export default function RiskDashboard() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">Risk Dashboard</h2>
      <RiskMetricsCards />
      <div className="grid grid-cols-2 gap-4">
        <DrawdownChart />
        <CorrelationMatrix />
      </div>
    </div>
  )
}
