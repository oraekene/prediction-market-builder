export type StrategyStatus = 'draft' | 'active' | 'paused' | 'archived'
export type StrategyMode = 'chat' | 'node' | 'hybrid' | 'automated'

export interface StrategyNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, unknown>
}

export interface StrategyEdge {
  id: string
  source: string
  target: string
}

export interface Strategy {
  id: string
  name: string
  description?: string
  status: StrategyStatus
  mode: StrategyMode
  nodes: StrategyNode[]
  edges: StrategyEdge[]
  risk_profile: Record<string, unknown>
  created_at: string
  updated_at: string
}
