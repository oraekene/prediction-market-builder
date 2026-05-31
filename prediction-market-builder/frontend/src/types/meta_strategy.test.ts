import { describe, it, expect } from 'vitest'
import {
  DEFAULT_SCORING_CONFIG,
  DEFAULT_PROMOTION_CONFIG,
  DEFAULT_CONFLUENCE_CONFIG,
} from './meta_strategy'

describe('DEFAULT_SCORING_CONFIG', () => {
  it('has expected shape with metrics', () => {
    expect(DEFAULT_SCORING_CONFIG).toHaveProperty('metrics')
    expect(DEFAULT_SCORING_CONFIG.metrics).toHaveProperty('sharpe')
    expect(DEFAULT_SCORING_CONFIG.metrics).toHaveProperty('win_rate')
    expect(DEFAULT_SCORING_CONFIG.metrics).toHaveProperty('profit_factor')
    expect(DEFAULT_SCORING_CONFIG.metrics).toHaveProperty('max_drawdown')
    expect(DEFAULT_SCORING_CONFIG.metrics).toHaveProperty('confidence')
    expect(DEFAULT_SCORING_CONFIG.metrics).toHaveProperty('expected_value')
    expect(DEFAULT_SCORING_CONFIG.metrics).toHaveProperty('signal_strength')
    expect(DEFAULT_SCORING_CONFIG.metrics).toHaveProperty('consistency')
  })

  it('weights sum to 100', () => {
    const values = Object.values(DEFAULT_SCORING_CONFIG.metrics)
    const total = values.reduce((a, b) => a + b, 0)
    expect(total).toBeCloseTo(1.0, 10)
  })
})

describe('DEFAULT_PROMOTION_CONFIG', () => {
  it('has expected shape', () => {
    expect(DEFAULT_PROMOTION_CONFIG).toHaveProperty('interval')
    expect(DEFAULT_PROMOTION_CONFIG).toHaveProperty('probation_hours')
    expect(DEFAULT_PROMOTION_CONFIG).toHaveProperty('evaluation_window_days')
  })

  it('defaults to daily interval', () => {
    expect(DEFAULT_PROMOTION_CONFIG.interval).toBe('daily')
  })
})

describe('DEFAULT_CONFLUENCE_CONFIG', () => {
  it('has expected shape', () => {
    expect(DEFAULT_CONFLUENCE_CONFIG).toHaveProperty('threshold')
    expect(DEFAULT_CONFLUENCE_CONFIG).toHaveProperty('source')
    expect(DEFAULT_CONFLUENCE_CONFIG).toHaveProperty('from_top')
    expect(DEFAULT_CONFLUENCE_CONFIG).toHaveProperty('manual_strategy_ids')
  })

  it('defaults to top_n source', () => {
    expect(DEFAULT_CONFLUENCE_CONFIG.source).toBe('top_n')
  })
})
