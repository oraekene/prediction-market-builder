import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatusBar from './StatusBar'

describe('StatusBar', () => {
  it('renders platform statuses', () => {
    render(<StatusBar />)
    expect(screen.getByText(/Polymarket/)).toBeTruthy()
    expect(screen.getByText(/Kalshi/)).toBeTruthy()
    expect(screen.getByText(/Drift/)).toBeTruthy()
  })

  it('shows a timestamp', () => {
    render(<StatusBar />)
    expect(screen.getByText(/Last updated/)).toBeTruthy()
  })
})
