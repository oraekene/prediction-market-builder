import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { IterationChart } from './IterationChart'

const sampleResults = [
  { iteration: 1, composite_score: 0.8, backtest_sharpe: 0.6, backtest_win_rate: 0.55, verdict: 'WARN' },
  { iteration: 2, composite_score: 1.2, backtest_sharpe: 0.9, backtest_win_rate: 0.6, verdict: 'KEPT' },
  { iteration: 3, composite_score: 0.4, backtest_sharpe: 0.3, backtest_win_rate: 0.4, verdict: 'REVERTED' },
]

describe('IterationChart', () => {
  it('renders without crashing', () => {
    const { container } = render(<IterationChart results={sampleResults} />)
    expect(container).toBeTruthy()
  })

  it('renders chart title', () => {
    render(<IterationChart results={sampleResults} />)
    expect(screen.getByText('Performance Trends')).toBeTruthy()
  })

  it('shows empty state when no results', () => {
    render(<IterationChart results={[]} />)
    expect(screen.getByText('No iteration data for chart')).toBeTruthy()
  })
})
