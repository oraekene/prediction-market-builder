import { useMetaStrategies } from '@/hooks/useMetaStrategies'
import MetaStrategyCard from './MetaStrategyCard'
import { useNavigate } from 'react-router-dom'
import { useCreateMetaStrategy } from '@/hooks/useMetaStrategies'

export default function MetaStrategyList() {
  const { data, isLoading, error } = useMetaStrategies()
  const create = useCreateMetaStrategy()
  const navigate = useNavigate()

  const metaStrategies = Array.isArray(data) ? data : []

  async function handleCreate() {
    const result = await create.mutateAsync({
      name: `Meta-Strategy ${metaStrategies.length + 1}`,
      description: 'New meta-strategy',
    })
    navigate(`/meta-strategies/${result.id}`)
  }

  if (isLoading) return <div className="text-gray-400">Loading meta-strategies...</div>
  if (error) return <div className="text-red-400">Error loading meta-strategies</div>

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Meta-Strategies</h1>
          <p className="mt-1 text-sm text-gray-400">
            Compete, compare, and combine strategies automatically
          </p>
        </div>
        <button
          onClick={handleCreate}
          disabled={create.isPending}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {create.isPending ? 'Creating...' : 'New Meta-Strategy'}
        </button>
      </div>

      {metaStrategies.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-700 p-12 text-center">
          <p className="text-gray-400">No meta-strategies yet.</p>
          <p className="mt-1 text-sm text-gray-500">
            Create one to group strategies, run competitions, or set up confluence trading.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {metaStrategies.map((ms: any) => (
            <MetaStrategyCard key={ms.id} metaStrategy={ms} />
          ))}
        </div>
      )}
    </div>
  )
}
