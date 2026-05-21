import { usePaperWallet, useResetWallet } from '@/hooks/usePaperTrading'
import { formatVolume } from '@/lib/utils'

export default function PaperWalletCard() {
  const { data: wallet, isLoading, error } = usePaperWallet()
  const resetMutation = useResetWallet()

  if (isLoading) return <div className="rounded-lg border border-gray-700 bg-gray-900 p-4"><p className="text-gray-400">Loading wallet...</p></div>
  if (error || !wallet) return <div className="rounded-lg border border-gray-700 bg-gray-900 p-4"><p className="text-red-400">Failed to load wallet</p></div>

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase text-gray-400">Paper Wallet</h3>
        <button
          onClick={() => resetMutation.mutate('default')}
          className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-400 hover:text-white hover:bg-gray-700"
        >
          Reset
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-gray-500">Balance</p>
          <p className="text-2xl font-bold text-white"></p>
        </div>
        <div>
          <p className="text-xs text-gray-500">P&L</p>
          <p className={	ext-2xl font-bold }>
            {wallet.pnl >= 0 ? '+' : ''}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Return</p>
          <p className={	ext-2xl font-bold }>
            {wallet.pnl_pct >= 0 ? '+' : ''}{wallet.pnl_pct}%
          </p>
        </div>
      </div>

      <div className="mt-3 flex gap-4 text-xs text-gray-500">
        <span>Initial: </span>
        <span>Open positions: {wallet.open_positions.length}</span>
        <span>Trades: {wallet.recent_trades.length}</span>
      </div>
    </div>
  )
}
