import { useState } from 'react'
import {
  useSafeWallets,
  useCreateSafeWallet,
  useTransferToSafe,
  useWithdrawalHistory,
} from '@/hooks/useWithdrawal'

export default function SafeWalletDashboard() {
  const { data: wallets = [], isLoading: walletsLoading } = useSafeWallets()
  const { data: history = [], isLoading: historyLoading } = useWithdrawalHistory()
  const createWallet = useCreateSafeWallet()
  const transferToSafe = useTransferToSafe()

  const [showTransferModal, setShowTransferModal] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [transferForm, setTransferForm] = useState({
    currency: 'USDC',
    amount: '',
    source: '',
  })
  const [createForm, setCreateForm] = useState({
    name: '',
    currency: 'USDC',
  })

  const totalProtected = wallets.reduce((sum, w) => sum + w.balance, 0)

  const handleTransfer = async () => {
    if (!transferForm.amount || !transferForm.source) return
    await transferToSafe.mutateAsync({
      currency: transferForm.currency,
      amount: parseFloat(transferForm.amount),
      source: transferForm.source,
    })
    setTransferForm({ currency: 'USDC', amount: '', source: '' })
    setShowTransferModal(false)
  }

  const handleCreateWallet = async () => {
    if (!createForm.name) return
    await createWallet.mutateAsync({
      name: createForm.name,
      currency: createForm.currency,
    })
    setCreateForm({ name: '', currency: 'USDC' })
    setShowCreateModal(false)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Safe Wallets</h1>
            <p className="text-gray-400 mt-1">Protect your profits in secure wallets</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium transition-colors"
          >
            + New Wallet
          </button>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <p className="text-sm text-gray-400 uppercase tracking-wide">Total Protected Capital</p>
          <p className="text-3xl font-bold mt-1">${totalProtected.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {walletsLoading ? (
            <div className="col-span-full text-center text-gray-500 py-8">Loading wallets...</div>
          ) : wallets.length === 0 ? (
            <div className="col-span-full text-center text-gray-500 py-8">
              No safe wallets yet. Create one to start protecting your capital.
            </div>
          ) : (
            wallets.map((wallet) => (
              <div
                key={wallet.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-lg">{wallet.name}</h3>
                    <p className="text-sm text-gray-400">{wallet.currency}</p>
                  </div>
                  {wallet.is_disconnected && (
                    <span className="text-xs bg-red-900/50 text-red-400 px-2 py-1 rounded">Disconnected</span>
                  )}
                </div>
                <p className="text-2xl font-bold mt-3">
                  ${wallet.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
                {wallet.address && (
                  <p className="text-xs text-gray-500 mt-2 truncate" title={wallet.address}>
                    {wallet.address}
                  </p>
                )}
                <button
                  onClick={() => {
                    setTransferForm((f) => ({ ...f, currency: wallet.currency || 'USDC' }))
                    setShowTransferModal(true)
                  }}
                  className="mt-3 w-full py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
                >
                  Transfer In
                </button>
              </div>
            ))
          )}
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-gray-800">
            <h2 className="font-semibold text-lg">Withdrawal History</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left px-5 py-3 font-medium">Date</th>
                  <th className="text-left px-5 py-3 font-medium">Amount</th>
                  <th className="text-left px-5 py-3 font-medium">Currency</th>
                  <th className="text-left px-5 py-3 font-medium">Source</th>
                  <th className="text-left px-5 py-3 font-medium">Trigger</th>
                  <th className="text-left px-5 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {historyLoading ? (
                  <tr>
                    <td colSpan={6} className="text-center text-gray-500 py-8">Loading history...</td>
                  </tr>
                ) : history.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center text-gray-500 py-8">No withdrawal records yet.</td>
                  </tr>
                ) : (
                  history.map((record) => (
                    <tr key={record.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="px-5 py-3">{new Date(record.created_at).toLocaleDateString()}</td>
                      <td className="px-5 py-3 font-medium">
                        ${record.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-5 py-3 text-gray-400">{record.currency}</td>
                      <td className="px-5 py-3 text-gray-400">{record.source}</td>
                      <td className="px-5 py-3 text-gray-400">{record.trigger_type}</td>
                      <td className="px-5 py-3">
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            record.status === 'completed'
                              ? 'bg-emerald-900/50 text-emerald-400'
                              : record.status === 'pending'
                              ? 'bg-yellow-900/50 text-yellow-400'
                              : 'bg-red-900/50 text-red-400'
                          }`}
                        >
                          {record.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showTransferModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold">Transfer to Safe Wallet</h2>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Source</label>
              <input
                type="text"
                value={transferForm.source}
                onChange={(e) => setTransferForm((f) => ({ ...f, source: e.target.value }))}
                placeholder="e.g. strategy-123, manual"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Amount</label>
              <input
                type="number"
                value={transferForm.amount}
                onChange={(e) => setTransferForm((f) => ({ ...f, amount: e.target.value }))}
                placeholder="0.00"
                min="0"
                step="0.01"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setShowTransferModal(false)}
                className="flex-1 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleTransfer}
                disabled={transferToSafe.isPending}
                className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {transferToSafe.isPending ? 'Transferring...' : 'Transfer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold">Create Safe Wallet</h2>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Name</label>
              <input
                type="text"
                value={createForm.name}
                onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Main Reserves"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Currency</label>
              <select
                value={createForm.currency}
                onChange={(e) => setCreateForm((f) => ({ ...f, currency: e.target.value }))}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-emerald-500"
              >
                <option value="USDC">USDC</option>
                <option value="USDT">USDT</option>
                <option value="DAI">DAI</option>
                <option value="USD">USD (Fiat)</option>
              </select>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateWallet}
                disabled={createWallet.isPending}
                className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {createWallet.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
