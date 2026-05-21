import { useState } from 'react'
import NodeCanvas from '@/components/strategies/NodeCanvas'
import type { NodeCanvasNode } from '@/components/strategies/NodeCanvas'
import NodePalette from '@/components/strategies/NodePalette'
import NodePropertyPanel from '@/components/strategies/NodePropertyPanel'
import StrategyList from '@/components/strategies/StrategyList'

export default function StrategiesPage() {
  const [selectedNode, setSelectedNode] = useState<NodeCanvasNode | null>(null)
  const [showCanvas, setShowCanvas] = useState(false)

  if (!showCanvas) {
    return (
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">Strategies</h1>
          <button
            onClick={() => setShowCanvas(true)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Create Strategy
          </button>
        </div>
        <StrategyList />
      </div>
    )
  }

  return (
    <div className="flex h-full">
      <NodePalette />
      <div className="flex-1">
        <NodeCanvas onNodeSelect={(node) => setSelectedNode(node)} />
      </div>
      <NodePropertyPanel selectedNode={selectedNode} />
    </div>
  )
}
