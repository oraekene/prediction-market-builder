import { useParams } from 'react-router-dom'
import MetaStrategyList from '@/components/meta-strategies/MetaStrategyList'
import MetaStrategyDetail from '@/components/meta-strategies/MetaStrategyDetail'

export default function MetaStrategiesPage() {
  const { id } = useParams<{ id: string }>()

  if (id) {
    return (
      <div className="mx-auto max-w-5xl">
        <MetaStrategyDetail />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl">
      <MetaStrategyList />
    </div>
  )
}
