import { useState, useCallback } from 'react'
import NodeCanvas from '@/components/strategies/NodeCanvas'
import type { NodeCanvasNode } from '@/components/strategies/NodeCanvas'
import NodePalette from '@/components/strategies/NodePalette'
import NodePropertyPanel from '@/components/strategies/NodePropertyPanel'
import StrategyList from '@/components/strategies/StrategyList'
import { useStrategy, useUpdateStrategy } from '@/hooks/useStrategies'

interface StrategyNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, unknown>
}

interface StrategyEdge {
  id: string
  source: string
  target: string
}

interface Strategy {
  id: string
  name: string
  description?: string | null
  status: string
  mode: string
  nodes: StrategyNode[]
  edges: StrategyEdge[]
}

export default function StrategiesPage() {
  const [selectedNode, setSelectedNode] = useState<NodeCanvasNode | null>(null)
  const [showCanvas, setShowCanvas] = useState(false)
  const [editingStrategyId, setEditingStrategyId] = useState<string | null>(null)

  const { data: editingStrategy } = useStrategy(editingStrategyId || '')
  const updateStrategy = useUpdateStrategy()

  const handleEditStrategy = useCallback((strategyId: string) => {
    setEditingStrategyId(strategyId)
    setShowCanvas(true)
  }, [])

  const handleCreateNew = useCallback(() => {
    setEditingStrategyId(null)
    setShowCanvas(true)
  }, [])

  const handleBackToList = useCallback(() => {
    setShowCanvas(false)
    setEditingStrategyId(null)
    setSelectedNode(null)
  }, [])

  const handleSave = useCallback((nodes: any[], edges: any[]) => {
    if (editingStrategyId) {
      updateStrategy.mutate({
        id: editingStrategyId,
        data: { nodes, edges },
      })
    }
  }, [editingStrategyId, updateStrategy])

  const handleNodeUpdate = useCallback((nodeId: string, newData: Record<string, unknown>) => {
    // Node updates are handled locally in NodeCanvas via setNodes
    // This callback is for external side effects if needed
  }, [])

  if (!showCanvas) {
    return (
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold">Strategies</h1>
          <button
            onClick={handleCreateNew}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Create Strategy
          </button>
        </div>
        <StrategyList onEditStrategy={handleEditStrategy} />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b border-gray-800 bg-gray-950 px-4 py-2">
        <button
          onClick={handleBackToList}
          className="rounded px-3 py-1 text-xs text-gray-400 hover:bg-gray-800 hover:text-white"
        >
          ← Back
        </button>
        <span className="text-sm font-medium text-white">
          {editingStrategy ? editingStrategy.name : 'New Strategy'}
        </span>
        {editingStrategy && (
          <span className="rounded bg-gray-800 px-2 py-0.5 text-[10px] text-gray-400">
            {editingStrategy.status}
          </span>
        )}
      </div>
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />
        <div className="flex-1">
          <NodeCanvas
            initialNodes={editingStrategy?.nodes}
            initialEdges={editingStrategy?.edges}
            onSave={handleSave}
            onNodeUpdate={handleNodeUpdate}
            onNodeSelect={(node) => setSelectedNode(node)}
          />
        </div>
        <NodePropertyPanel selectedNode={selectedNode} />
      </div>
    </div>
  )
}
