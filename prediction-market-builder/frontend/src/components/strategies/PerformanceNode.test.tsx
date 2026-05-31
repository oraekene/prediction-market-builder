import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import PerformanceNode, { formatValue } from './PerformanceNode'

vi.mock('@xyflow/react', () => ({
  Handle: () => null,
  Position: { Right: 'right', Left: 'left', Top: 'top', Bottom: 'bottom' },
}))

describe('formatValue', () => {
  it('formats percentage metrics', () => {
    expect(formatValue('win-rate', 0.75)).toBe('75.0%')
    expect(formatValue('kelly-optimal', 0.5)).toBe('50.0%')
    expect(formatValue('max-drawdown', 0.12)).toBe('12.0%')
  })

  it('formats dollar metrics', () => {
    expect(formatValue('total-pnl', 2500.5)).toBe('$2500.50')
    expect(formatValue('edge', 0.05)).toBe('$0.05')
    expect(formatValue('largest-win', 1000)).toBe('$1000.00')
    expect(formatValue('current-balance', 50000)).toBe('$50000.00')
  })

  it('formats count metrics as integers', () => {
    expect(formatValue('trade-count', 25)).toBe('25')
    expect(formatValue('consecutive-streak', 7)).toBe('7')
  })

  it('formats default metrics to 4 decimals', () => {
    expect(formatValue('sharpe', 1.5)).toBe('1.5000')
    expect(formatValue('sortino', 2.2)).toBe('2.2000')
  })
})

describe('PerformanceNode', () => {
  it('renders metric label from registry', () => {
    render(<PerformanceNode data={{ metric: 'sharpe', value: 1.5 }} />)
    expect(screen.getByText('Sharpe')).toBeTruthy()
  })

  it('renders unknown metric label via fallback label', () => {
    render(<PerformanceNode data={{ metric: 'unknown_metric', label: 'Custom', value: 42 }} />)
    expect(screen.getByText('Custom')).toBeTruthy()
  })

  it('renders formatted value', () => {
    render(<PerformanceNode data={{ metric: 'sharpe', value: 1.5 }} />)
    expect(screen.getByText('1.5000')).toBeTruthy()
  })

  it('shows dash when value is null', () => {
    render(<PerformanceNode data={{ metric: 'sharpe', value: null }} />)
    expect(screen.getByText('—')).toBeTruthy()
  })

  it('shows window size when provided', () => {
    render(<PerformanceNode data={{ metric: 'sharpe', value: 1.5, window: 20 }} />)
    expect(screen.getByText('window: 20')).toBeTruthy()
  })

  it('hides window when zero', () => {
    render(<PerformanceNode data={{ metric: 'sharpe', value: 1.5, window: 0 }} />)
    expect(screen.queryByText(/window/)).toBeNull()
  })
})
