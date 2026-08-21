import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ConditionNode from './ConditionNode'

vi.mock('@xyflow/react', () => ({
  Handle: () => null,
  Position: { Right: 'right', Left: 'left', Top: 'top', Bottom: 'bottom' },
}))

describe('ConditionNode', () => {
  it('renders with label', () => {
    render(<ConditionNode data={{ label: 'Threshold Check' }} />)
    expect(screen.getByText('Threshold Check')).toBeTruthy()
  })

  it('renders hardcoded Condition badge', () => {
    render(<ConditionNode data={{ label: 'Threshold Check' }} />)
    expect(screen.getByText('Condition')).toBeTruthy()
  })

  it('renders backendType when provided', () => {
    render(<ConditionNode data={{ label: 'Threshold', backendType: 'threshold_condition' }} />)
    expect(screen.getByText('threshold_condition')).toBeTruthy()
  })
})
