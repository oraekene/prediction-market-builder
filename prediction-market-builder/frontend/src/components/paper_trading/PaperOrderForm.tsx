import { useState } from 'react'
import { usePlacePaperOrder } from '@/hooks/usePaperTrading'
import { usePaperWallet } from '@/hooks/usePaperTrading'

export default function PaperOrderForm() {
  const { data: wallet } = usePaperWallet()
  const placeOrder = usePlacePaperOrder()
  const [marketId, setMarketId] = useState('')
  const [platform, setPlatform] = useState('polymarket')
  const [side, setSide] = useState('buy')
  const [price, setPrice] = useState('0.50')
  const [amount, setAmount] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!wallet || !amount) return
    placeOrder.mutate({
      wallet_id: wallet.id,
      platform,
      market_id: marketId,
      market_title: marketId,
      side,
      amount: parseFloat(amount),
      price: parseFloat(price),
    })
    setAmount('')
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-gray-700 bg-gray-900 p-4 space-y-3">
      <h3 className="text-sm font-semibold uppercase text-gray-400">Place Paper Order</h3>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Market ID</label>
          <input
            type="text"
            value={marketId}
            onChange={(e) => setMarketId(e.target.value)}
            placeholder="e.g. 0x1234..."
            className="w-full rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            required
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Platform</label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="w-full rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-sm text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="polymarket">Polymarket</option>
            <option value="kalshi">Kalshi</option>
            <option value="drift">Drift</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Side</label>
          <div className="flex rounded border border-gray-700 overflow-hidden">
            <button
              type="button"
              onClick={() => setSide('buy')}
              className={lex-1 py-1.5 text-xs font-medium }
            >
              Yes
            </button>
            <button
              type="button"
              onClick={() => setSide('sell')}
              className={lex-1 py-1.5 text-xs font-medium }
            >
              No
            </button>
          </div>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Price</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            max="0.99"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-sm text-white focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Amount ($)</label>
          <input
            type="number"
            step="10"
            min="1"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="100"
            className="w-full rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-sm text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            required
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">
          Balance: 
        </span>
        <button
          type="submit"
          disabled={placeOrder.isPending}
          className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {placeOrder.isPending ? 'Placing...' : 'Place Order'}
        </button>
      </div>

      {placeOrder.data && (
        <div className={ounded p-2 text-xs }>
          {placeOrder.data.success
            ? Order filled at {placeOrder.data.order?.fill_price} | Slippage: %
            : placeOrder.data.error}
        </div>
      )}
    </form>
  )
}
