import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MarketDetail from './MarketDetail'

describe('MarketDetail', () => {
  it('renders market ID', () => {
    render(<MarketDetail marketId="test-123" />)
    expect(screen.getByText(/Market Detail: test-123/)).toBeTruthy()
  })

  it('renders placeholder message', () => {
    render(<MarketDetail marketId="test-123" />)
    expect(screen.getByText(/Full detail view coming/)).toBeTruthy()
  })
})
