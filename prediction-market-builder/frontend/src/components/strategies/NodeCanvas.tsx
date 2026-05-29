import { useCallback, useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import PerformanceNode from './PerformanceNode'
import RiskNode from './RiskNode'
import ActionNode from './ActionNode'
import SourceNode from './SourceNode'
import ConditionNode from './ConditionNode'
import { getNodeType, getDefaultConfig } from '@/lib/nodeTypeRegistry'

interface NodeData {
  label: string
  backendType?: string
  [key: string]: unknown
}

interface FlowNode {
  id: string
  type?: string
  position: { x: number; y: number }
  data: NodeData
}

interface FlowEdge {
  id: string
  source: string
  target: string
}

interface Connection {
  source: string | null
  target: string | null
  sourceHandle: string | null
  targetHandle: string | null
}

const defaultNodes: FlowNode[] = [
  {
    id: 'source-1',
    type: 'default',
    position: { x: 50, y: 100 },
    data: { label: 'Polymarket Data' },
  },
  {
    id: 'condition-1',
    type: 'default',
    position: { x: 300, y: 100 },
    data: { label: 'Odds < 45%' },
  },
  {
    id: 'action-1',
    type: 'default',
    position: { x: 550, y: 100 },
    data: { label: 'Place Bet' },
  },
]

const defaultEdges: FlowEdge[] = [
  { id: 'e1', source: 'source-1', target: 'condition-1' },
  { id: 'e2', source: 'condition-1', target: 'action-1' },
]

interface NodeCanvasProps {
  initialNodes?: FlowNode[]
  initialEdges?: FlowEdge[]
  onSave?: (nodes: FlowNode[], edges: FlowEdge[]) => void
  onNodeUpdate?: (nodeId: string, newData: Partial<NodeData>) => void
  onNodeSelect: (node: FlowNode | null) => void
}

export type NodeCanvasNode = FlowNode

const labelToMetric: Record<string, string> = {
  'Current Balance': 'current-balance',
  'Total P&L': 'total-pnl',
  'Win Rate': 'win-rate',
  'Avg R:R': 'avg-rr',
  'Sharpe': 'sharpe',
  'Sortino': 'sortino',
  'Calmar': 'calmar',
  'Max Drawdown': 'max-drawdown',
  'Profit Factor': 'profit-factor',
  'Kelly %': 'kelly-optimal',
  'Edge': 'edge',
  'Brier Score': 'brier-score',
  'Trade Count': 'trade-count',
  'SQN': 'sqn',
  'Recovery Factor': 'recovery-factor',
  'Largest Win': 'largest-win',
  'Largest Loss': 'largest-loss',
  'Consecutive Streak': 'consecutive-streak',
}

const nodeTypes = {
  performance: PerformanceNode,
  risk: RiskNode,
  action: ActionNode,
  source: SourceNode,
  condition: ConditionNode,
}

export default function NodeCanvas({ initialNodes, initialEdges, onSave, onNodeUpdate, onNodeSelect }: NodeCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(
    (initialNodes && initialNodes.length > 0 ? initialNodes : defaultNodes) as any
  )
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    (initialEdges && initialEdges.length > 0 ? initialEdges : defaultEdges) as any
  )

  useEffect(() => {
    if (initialNodes && initialNodes.length > 0) {
      setNodes(initialNodes as any)
    }
    if (initialEdges && initialEdges.length > 0) {
      setEdges(initialEdges as any)
    }
  }, [initialNodes, initialEdges, setNodes, setEdges])

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave(nodes as FlowNode[], edges as FlowEdge[])
    }
  }, [nodes, edges, onSave])

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds: any[]) => {
        const newEdge = {
          id: `e-${connection.source}-${connection.target}`,
          source: connection.source || '',
          target: connection.target || '',
        }
        return [...eds, newEdge]
      })
    },
    [setEdges],
  )

  const onSelectionChange = useCallback(
    ({ nodes: selectedNodes }: { nodes: FlowNode[] }) => {
      onNodeSelect(selectedNodes[0] || null)
    },
    [onNodeSelect],
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      const label = event.dataTransfer.getData('application/reactflow')
      const flowType = event.dataTransfer.getData('application/reactflow-type') || 'default'
      if (!label) return
      const position = { x: event.clientX - 100, y: event.clientY - 50 }
      const metric = labelToMetric[label]
      const nodeDef = getNodeType(label)
      const defaultConfig = getDefaultConfig(label)
      const category = nodeDef?.category || ''
      let visualType = flowType
      if (flowType === 'default' && nodeDef) {
        if (category.startsWith('Risk')) visualType = 'risk'
        else if (category === 'Actions') visualType = 'action'
        else if (category === 'Sources') visualType = 'source'
        else if (category === 'Conditions') visualType = 'condition'
        else if (category === 'Auto-Withdrawal') visualType = 'action'
        else if (category === 'Analysis') visualType = 'condition'
      }
      const newNode: FlowNode = {
        id: `${label.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}`,
        type: visualType,
        position,
        data: {
          label,
          backendType: nodeDef?.backendType || label,
          ...defaultConfig,
          ...(metric ? { metric, window: 50, value: null } : {}),
        },
      }
      setNodes((nds: FlowNode[]) => nds.concat(newNode))
    },
    [setNodes],
  )

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-800 bg-gray-950 px-4 py-2">
        <span className="text-xs text-gray-500">
          {nodes.length} nodes · {edges.length} connections
        </span>
        {onSave && (
          <button
            onClick={handleSave}
            className="rounded bg-blue-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            Save Strategy
          </button>
        )}
      </div>
      <div className="flex-1">
        <ReactFlow
          nodes={nodes as any}
          edges={edges as any}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange as any}
          onEdgesChange={onEdgesChange as any}
          onConnect={onConnect as any}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onSelectionChange={onSelectionChange as any}
          fitView
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    </div>
  )
}
