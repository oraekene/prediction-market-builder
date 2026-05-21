import type { NodeCanvasNode } from './NodeCanvas'

interface Props {
  selectedNode: NodeCanvasNode | null
}

export default function NodePropertyPanel({ selectedNode }: Props) {
  if (!selectedNode) {
    return (
      <aside className="w-64 border-l border-gray-800 bg-gray-950 p-4">
        <p className="text-sm text-gray-500">Select a node to configure</p>
      </aside>
    )
  }

  return (
    <aside className="w-64 border-l border-gray-800 bg-gray-950 p-4 overflow-y-auto">
      <h3 className="mb-4 text-sm font-semibold text-white">
        Configure: {selectedNode.data.label}
      </h3>
      <div className="space-y-4">
        <label className="block">
          <span className="text-xs text-gray-400">Parameter</span>
          <input
            className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            placeholder="Value"
          />
        </label>
        <label className="block">
          <span className="text-xs text-gray-400">Description</span>
          <textarea
            className="mt-1 w-full rounded border border-gray-700 bg-gray-800 px-2.5 py-1.5 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            rows={3}
            placeholder="Optional description"
          />
        </label>
        <div className="border-t border-gray-800 pt-4">
          <h4 className="mb-2 text-xs font-medium text-gray-500">Output Type</h4>
          <span className="rounded bg-gray-800 px-2 py-0.5 text-xs text-blue-400">
            {selectedNode.type === 'default' ? 'Data' : 'Mixed'}
          </span>
        </div>
      </div>
    </aside>
  )
}
