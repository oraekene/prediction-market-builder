export type MarketPlatform = 'polymarket' | 'kalshi' | 'drift'
export type MarketStatus = 'open' | 'closed' | 'resolved'

export interface Market {
  id: string
  platform: MarketPlatform
  platform_market_id: string
  title: string
  description?: string
  category?: string
  current_odds: number
  bid?: number
  ask?: number
  volume: number
  liquidity: number
  participants: number
  close_time?: string
  status: MarketStatus
  outcomes: string[]
  last_updated: string
}
