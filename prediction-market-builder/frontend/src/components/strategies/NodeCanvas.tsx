import { useCallback } from 'react'
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

interface NodeData {
  label: string
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

const initialNodes: FlowNode[] = [
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

const initialEdges: FlowEdge[] = [
  { id: 'e1', source: 'source-1', target: 'condition-1' },
  { id: 'e2', source: 'condition-1', target: 'action-1' },
]

interface NodeCanvasProps {
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
}

export default function NodeCanvas({ onNodeSelect }: NodeCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes as any)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges as any)

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
      const newNode: FlowNode = {
        id: `${label.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}`,
        type: flowType,
        position,
        data: metric
          ? { label, metric, window: 50, value: null }
          : { label },
      }
      setNodes((nds: FlowNode[]) => nds.concat(newNode))
    },
    [setNodes],
  )

  return (
    <div className="h-full w-full">
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
  )
}
