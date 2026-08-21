import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import MetaStrategyCard from './MetaStrategyCard'
import type { MetaStrategy } from '@/types/meta_strategy'

function createMetaStrategy(overrides?: Partial<MetaStrategy>): MetaStrategy {
  return {
    id: 'meta-1',
    user_id: 'user-1',
    name: 'Test Meta',
    description: 'A test meta-strategy',
    mode: 'standard',
    status: 'active',
    strategy_ids: ['s1', 's2', 's3'],
    scoring_config: { metrics: { sharpe: 0.2, win_rate: 0.15, profit_factor: 0.15, max_drawdown: 0.1, confidence: 0.1, expected_value: 0.1, signal_strength: 0.1, consistency: 0.1 } },
    promotion_config: { interval: 'daily', interval_days: null, probation_hours: 48, evaluation_window_days: 30 },
    confluence_config: { threshold: 3, source: 'top_n', from_top: 5, manual_strategy_ids: [] },
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-15T10:00:00Z',
    ...overrides,
  }
}

function renderCard(ms: MetaStrategy) {
  return render(
    <MemoryRouter>
      <MetaStrategyCard metaStrategy={ms} />
    </MemoryRouter>,
  )
}

describe('MetaStrategyCard', () => {
  it('renders name and status', () => {
    renderCard(createMetaStrategy())
    expect(screen.getByText('Test Meta')).toBeTruthy()
    expect(screen.getByText('active')).toBeTruthy()
  })

  it('renders mode label', () => {
    renderCard(createMetaStrategy({ mode: 'competition' }))
    expect(screen.getByText('Competition')).toBeTruthy()
  })

  it('renders description when provided', () => {
    renderCard(createMetaStrategy())
    expect(screen.getByText('A test meta-strategy')).toBeTruthy()
  })

  it('renders strategy count', () => {
    renderCard(createMetaStrategy())
    expect(screen.getByText('3 strategies in pool')).toBeTruthy()
  })

  it('shows winner indicator when winner exists', () => {
    renderCard(createMetaStrategy({ current_winner_id: 's1' }))
    expect(screen.getByText('Active winner')).toBeTruthy()
  })

  it('shows no winner when no winner', () => {
    renderCard(createMetaStrategy())
    expect(screen.getByText('No winner')).toBeTruthy()
  })
})
