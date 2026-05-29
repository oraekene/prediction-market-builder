export interface SafeWallet {
  id: string
  user_id: string
  name: string
  currency: string
  balance: number
  address?: string | null
  is_disconnected: boolean
  created_at: string
  updated_at: string
}

export interface WithdrawalRecord {
  id: string
  user_id: string
  safe_wallet_id: string
  strategy_id?: string | null
  amount: number
  currency: string
  source: string
  trigger_type: string
  trigger_step_id?: string | null
  status: string
  created_at: string
}

export interface WithdrawalCondition {
  type: string
  amount?: number
  pct?: number
  threshold?: number
}

export interface WithdrawalAction {
  type: string
  pct?: number
  amount?: number
  currency?: string
  stablecoin?: string
}

export interface WithdrawalStep {
  id: string
  condition: WithdrawalCondition
  action: WithdrawalAction
  once?: boolean
  cooldown_seconds?: number
  sequential?: boolean
}

export interface WithdrawalStrategy {
  id: string
  user_id: string
  name: string
  description?: string | null
  is_active: boolean
  steps: WithdrawalStep[]
  current_step_index: number
  step_states: Record<string, { status: string; last_fired?: string }>
  safe_wallet_id?: string | null
  created_at: string
  updated_at: string
}
