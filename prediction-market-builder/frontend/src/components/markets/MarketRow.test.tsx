import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MarketRow from './MarketRow'
import { type ReactNode } from 'react'

function TableWrap({ children }: { children: ReactNode }) {
  return <table><tbody>{children}</tbody></table>
}

const baseMarket = {
  title: 'Will BTC exceed $100k?',
  category: 'Crypto',
  platform: 'polymarket',
  current_odds: 0.65,
  volume: 1_500_000,
  close_time: '2026-12-31T23:59:59Z',
  platform_market_id: 'm-1',
}

describe('MarketRow', () => {
  it('renders market title and platform', () => {
    render(<TableWrap><MarketRow market={baseMarket} /></TableWrap>)
    expect(screen.getByText('Will BTC exceed $100k?')).toBeTruthy()
    expect(screen.getByText('polymarket')).toBeTruthy()
  })

  it('renders category when provided', () => {
    render(<TableWrap><MarketRow market={baseMarket} /></TableWrap>)
    expect(screen.getByText('Crypto')).toBeTruthy()
  })

  it('formats odds based on current_odds', () => {
    render(<TableWrap><MarketRow market={baseMarket} /></TableWrap>)
    expect(screen.getByText('65.0%')).toBeTruthy()
  })

  it('formats volume', () => {
    render(<TableWrap><MarketRow market={baseMarket} /></TableWrap>)
    expect(screen.getByText('1.5M')).toBeTruthy()
  })

  it('shows dash when no close_time', () => {
    const market = { ...baseMarket, close_time: undefined }
    render(<TableWrap><MarketRow market={market} /></TableWrap>)
    expect(screen.getByText('-')).toBeTruthy()
  })
})
