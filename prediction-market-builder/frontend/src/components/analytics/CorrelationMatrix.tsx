import { useCorrelation } from '@/hooks/useRisk'

export default function CorrelationMatrix() {
  const { data, isLoading } = useCorrelation()

  if (isLoading) return <p className="text-sm text-gray-400">Loading correlations...</p>
  if (!data?.pairs?.length) return <p className="text-sm text-gray-400">Not enough trade data for correlation analysis.</p>

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-gray-300">Correlation Matrix</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-400">
              <th className="px-3 py-1 text-left">Asset A</th>
              <th className="px-3 py-1 text-left">Asset B</th>
              <th className="px-3 py-1 text-right">Correlation</th>
            </tr>
          </thead>
          <tbody>
            {data.pairs.slice(0, 20).map((pair, i) => (
              <tr key={i} className="border-t border-gray-700">
                <td className="px-3 py-1 text-gray-300">{pair.asset_a.slice(0, 16)}</td>
                <td className="px-3 py-1 text-gray-300">{pair.asset_b.slice(0, 16)}</td>
                <td className={`px-3 py-1 text-right ${Math.abs(pair.correlation) > 0.7 ? 'text-red-400' : 'text-gray-300'}`}>
                  {pair.correlation.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
