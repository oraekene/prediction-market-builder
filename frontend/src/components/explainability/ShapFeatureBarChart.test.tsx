import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ShapFeatureBarChart from './ShapFeatureBarChart'

describe('ShapFeatureBarChart', () => {
  it('renders feature bars ranked by importance', () => {
    const importance = { feature_a: 0.5, feature_b: 0.3 }
    const ranking = ['feature_a', 'feature_b']
    render(<ShapFeatureBarChart importance={importance} ranking={ranking} />)
    expect(screen.getByText('feature_a')).toBeTruthy()
    expect(screen.getByText('feature_b')).toBeTruthy()
  })

  it('shows formatted percentage values', () => {
    const importance = { feature_a: 0.5 }
    render(<ShapFeatureBarChart importance={importance} ranking={['feature_a']} />)
    expect(screen.getByText('50.00%')).toBeTruthy()
  })

  it('shows empty state when no ranking', () => {
    render(<ShapFeatureBarChart importance={{}} ranking={[]} />)
    expect(screen.getByText('No feature importance data')).toBeTruthy()
  })
})
