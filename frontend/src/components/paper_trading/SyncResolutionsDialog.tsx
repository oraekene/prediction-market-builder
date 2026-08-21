import { useState } from 'react'
import { useSyncResolutions } from '@/hooks/usePaperTrading'

export default function SyncResolutionsDialog({ onClose }: { onClose: () => void }) {
  const [rows, setRows] = useState([{ market_id: '', platform: 'polymarket', outcome: 'yes' }])
  const syncMutation = useSyncResolutions()

  function updateRow(index: number, field: string, value: string) {
    const updated = rows.map((r, i) => (i === index ? { ...r, [field]: value } : r))
    setRows(updated)
  }

  function addRow() {
    setRows([...rows, { market_id: '', platform: 'polymarket', outcome: 'yes' }])
  }

  function removeRow(index: number) {
    setRows(rows.filter((_, i) => i !== index))
  }

  function handleSync() {
    const valid = rows.filter((r) => r.market_id.trim())
    if (valid.length > 0) {
      syncMutation.mutate(valid, {
        onSuccess: () => onClose(),
      })
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="w-full max-w-lg rounded-lg border border-gray-700 bg-gray-900 p-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-sm font-semibold uppercase text-gray-400 mb-3">Sync Market Resolutions</h3>
        <p className="text-xs text-gray-500 mb-3">Mark resolved markets so the system can compute calibration (Brier score).</p>

        <div className="space-y-2 max-h-60 overflow-y-auto mb-3">
          {rows.map((row, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input
                type="text"
                value={row.market_id}
                onChange={(e) => updateRow(i, 'market_id', e.target.value)}
                placeholder="market-id"
                className="flex-1 rounded border border-gray-700 bg-gray-800 px-2 py-1.5 text-xs text-white placeholder-gray-600 focus:border-blue-500 focus:outline-none"
              />
              <select
                value={row.platform}
                onChange={(e) => updateRow(i, 'platform', e.target.value)}
                className="rounded border border-gray-700 bg-gray-800 px-1 py-1.5 text-xs text-white focus:border-blue-500 focus:outline-none"
              >
                <option value="polymarket">Poly</option>
                <option value="kalshi">Kalshi</option>
                <option value="drift">Drift</option>
              </select>
              <select
                value={row.outcome}
                onChange={(e) => updateRow(i, 'outcome', e.target.value)}
                className="rounded border border-gray-700 bg-gray-800 px-1 py-1.5 text-xs text-white focus:border-blue-500 focus:outline-none"
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
              <button onClick={() => removeRow(i)} className="text-red-400 hover:text-red-300 text-sm px-1">✕</button>
            </div>
          ))}
        </div>

        <div className="flex gap-2 justify-between">
          <button onClick={addRow} className="rounded px-3 py-1.5 text-xs text-blue-400 hover:bg-blue-900/30">
            + Add Market
          </button>
          <div className="flex gap-2">
            <button onClick={onClose} className="rounded border border-gray-700 px-3 py-1.5 text-xs text-gray-400 hover:text-white">
              Cancel
            </button>
            <button
              onClick={handleSync}
              disabled={syncMutation.isPending}
              className="rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {syncMutation.isPending ? 'Syncing...' : syncMutation.data ? `Updated ${syncMutation.data.updated}` : 'Sync'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
