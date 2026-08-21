import { usePaperOrders, useCancelPaperOrder } from '@/hooks/usePaperTrading'
import { usePaperWallet } from '@/hooks/usePaperTrading'

export default function PaperOrderList() {
  const { data: wallet } = usePaperWallet()
  const { data, isLoading } = usePaperOrders(wallet?.id)
  const cancelMutation = useCancelPaperOrder()

  if (isLoading) return <div className="text-sm text-gray-400 py-4">Loading orders...</div>
  if (!data?.orders?.length) return <div className="text-sm text-gray-500 py-4">No orders yet. Place one above.</div>

  function statusStyle(status: string): string {
    switch (status) {
      case 'filled': return 'bg-green-900/50 text-green-300'
      case 'partial': return 'bg-yellow-900/50 text-yellow-300'
      case 'cancelled': return 'bg-gray-800 text-gray-500'
      default: return 'bg-blue-900/50 text-blue-300'
    }
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 bg-gray-950 text-left text-xs uppercase text-gray-500">
            <th className="px-3 py-2 font-medium">Market</th>
            <th className="px-3 py-2 font-medium">Side</th>
            <th className="px-3 py-2 font-medium">Price</th>
            <th className="px-3 py-2 font-medium">Amount</th>
            <th className="px-3 py-2 font-medium">Filled</th>
            <th className="px-3 py-2 font-medium">Status</th>
            <th className="px-3 py-2 font-medium">P&L</th>
            <th className="px-3 py-2 font-medium"></th>
          </tr>
        </thead>
        <tbody>
          {data.orders.map((order: any) => (
            <tr key={order.id} className="border-b border-gray-800 hover:bg-gray-800/50">
              <td className="px-3 py-2 max-w-[200px] truncate text-gray-300">{order.market_title || order.market_id}</td>
              <td className={`px-3 py-2 font-mono ${order.side === 'buy' || order.side === 'yes' ? 'text-green-400' : 'text-red-400'}`}>
                {order.side}
              </td>
              <td className="px-3 py-2 font-mono text-gray-300">{order.price.toFixed(2)}</td>
              <td className="px-3 py-2 font-mono text-gray-300">${order.amount.toFixed(2)}</td>
              <td className="px-3 py-2 font-mono text-gray-300">${order.filled_amount.toFixed(2)}</td>
              <td className="px-3 py-2">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusStyle(order.status)}`}>
                  {order.status}
                </span>
              </td>
              <td className={`px-3 py-2 font-mono ${order.pnl != null ? (order.pnl >= 0 ? 'text-green-400' : 'text-red-400') : 'text-gray-600'}`}>
                {order.pnl != null ? `$${order.pnl.toFixed(2)}` : '-'}
              </td>
              <td className="px-3 py-2">
                {(order.status === 'pending' || order.status === 'partial') && (
                  <button
                    onClick={() => cancelMutation.mutate(order.id)}
                    className="rounded px-2 py-0.5 text-xs text-red-400 hover:bg-red-900/30"
                  >
                    Cancel
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
