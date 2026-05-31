import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import SourceNode from './SourceNode'

vi.mock('@xyflow/react', () => ({
  Handle: () => null,
  Position: { Right: 'right', Left: 'left', Top: 'top', Bottom: 'bottom' },
}))

describe('SourceNode', () => {
  it('renders with label', () => {
    render(<SourceNode data={{ label: 'Polymarket' }} />)
    expect(screen.getByText('Polymarket')).toBeTruthy()
  })

  it('renders hardcoded Source badge', () => {
    render(<SourceNode data={{ label: 'Polymarket' }} />)
    expect(screen.getByText('Source')).toBeTruthy()
  })

  it('renders backendType when provided', () => {
    render(<SourceNode data={{ label: 'Polymarket', backendType: 'polymarket_source' }} />)
    expect(screen.getByText('polymarket_source')).toBeTruthy()
  })
})
