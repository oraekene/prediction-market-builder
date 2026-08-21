import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import RiskNode from './RiskNode'

vi.mock('@xyflow/react', () => ({
  Handle: () => null,
  Position: { Right: 'right', Left: 'left', Top: 'top', Bottom: 'bottom' },
}))

describe('RiskNode', () => {
  it('renders with label', () => {
    render(<RiskNode data={{ label: 'Stop-Loss' }} />)
    expect(screen.getByText('Stop-Loss')).toBeTruthy()
  })

  it('renders hardcoded Risk badge', () => {
    render(<RiskNode data={{ label: 'Stop-Loss' }} />)
    expect(screen.getByText('Risk')).toBeTruthy()
  })

  it('renders backendType when provided', () => {
    render(<RiskNode data={{ label: 'Stop-Loss', backendType: 'stop_loss' }} />)
    expect(screen.getByText('stop_loss')).toBeTruthy()
  })

  it('shows Triggered badge when data.triggered is true', () => {
    render(<RiskNode data={{ label: 'Stop-Loss', triggered: true }} />)
    expect(screen.getByText('Triggered')).toBeTruthy()
  })

  it('hides Triggered badge when not triggered', () => {
    render(<RiskNode data={{ label: 'Stop-Loss', triggered: false }} />)
    expect(screen.queryByText('Triggered')).toBeNull()
  })
})
