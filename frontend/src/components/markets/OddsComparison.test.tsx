import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import OddsComparison from './OddsComparison'

describe('OddsComparison', () => {
  it('renders title', () => {
    render(<OddsComparison />)
    expect(screen.getByText('Cross-Platform Odds')).toBeTruthy()
  })

  it('renders placeholder message', () => {
    render(<OddsComparison />)
    expect(screen.getByText(/Odds comparison across platforms/)).toBeTruthy()
  })
})
