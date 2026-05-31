import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Sidebar from './Sidebar'

describe('Sidebar', () => {
  it('renders all filter buttons', () => {
    render(<Sidebar />)
    expect(screen.getByText('All Markets')).toBeTruthy()
    expect(screen.getByText('Politics')).toBeTruthy()
    expect(screen.getByText('Economy')).toBeTruthy()
    expect(screen.getByText('Crypto')).toBeTruthy()
    expect(screen.getByText('Sports')).toBeTruthy()
    expect(screen.getByText('Watchlist')).toBeTruthy()
  })

  it('highlights active section on click', async () => {
    render(<Sidebar />)
    const cryptoBtn = screen.getByText('Crypto')
    await userEvent.click(cryptoBtn)
    expect(cryptoBtn.className).toContain('bg-gray-800 text-white')
  })

  it('unhighlights previously active section', async () => {
    render(<Sidebar />)
    const allMarkets = screen.getByText('All Markets')
    const cryptoBtn = screen.getByText('Crypto')
    await userEvent.click(cryptoBtn)
    expect(allMarkets.className).not.toContain('bg-gray-800')
  })
})
