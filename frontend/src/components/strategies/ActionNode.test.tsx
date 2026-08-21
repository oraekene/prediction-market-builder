import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ActionNode from './ActionNode'

vi.mock('@xyflow/react', () => ({
  Handle: () => null,
  Position: { Right: 'right', Left: 'left', Top: 'top', Bottom: 'bottom' },
}))

describe('ActionNode', () => {
  it('renders with label', () => {
    render(<ActionNode data={{ label: 'Place Bet' }} />)
    expect(screen.getByText('Place Bet')).toBeTruthy()
  })

  it('renders hardcoded Action badge', () => {
    render(<ActionNode data={{ label: 'Place Bet' }} />)
    expect(screen.getByText('Action')).toBeTruthy()
  })

  it('renders backendType when provided', () => {
    render(<ActionNode data={{ label: 'Place Bet', backendType: 'place_bet' }} />)
    expect(screen.getByText('place_bet')).toBeTruthy()
  })
})
