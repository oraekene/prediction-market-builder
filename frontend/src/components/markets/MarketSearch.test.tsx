import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MarketSearch from './MarketSearch'

describe('MarketSearch', () => {
  it('renders search input', () => {
    render(<MarketSearch />)
    expect(screen.getByPlaceholderText('Search markets...')).toBeTruthy()
  })

  it('calls onSearch when typing', async () => {
    const onSearch = vi.fn()
    render(<MarketSearch onSearch={onSearch} />)
    const input = screen.getByPlaceholderText('Search markets...')
    await userEvent.type(input, 'BTC')
    expect(onSearch).toHaveBeenCalledTimes(3)
    expect(onSearch).toHaveBeenLastCalledWith('BTC')
  })
})
