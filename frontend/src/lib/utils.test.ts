import { describe, it, expect } from 'vitest'
import { cn, formatOdds, formatVolume, formatTime } from './utils'

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('px-4', 'py-2')).toBe('px-4 py-2')
  })

  it('handles conditional classes', () => {
    expect(cn('base', false && 'hidden', 'visible')).toBe('base visible')
  })

  it('resolves tailwind conflicts', () => {
    expect(cn('px-4', 'px-2')).toBe('px-2')
  })
})

describe('formatOdds', () => {
  it('formats as percentage', () => {
    expect(formatOdds(0.75)).toBe('75.0%')
  })

  it('handles zero', () => {
    expect(formatOdds(0)).toBe('0.0%')
  })

  it('handles one', () => {
    expect(formatOdds(1)).toBe('100.0%')
  })
})

describe('formatVolume', () => {
  it('formats millions', () => {
    expect(formatVolume(1_500_000)).toBe('1.5M')
  })

  it('formats thousands', () => {
    expect(formatVolume(2_500)).toBe('2.5K')
  })

  it('returns raw number for small values', () => {
    expect(formatVolume(500)).toBe('500')
  })

  it('handles zero', () => {
    expect(formatVolume(0)).toBe('0')
  })
})

describe('formatTime', () => {
  it('formats ISO date string', () => {
    const result = formatTime('2026-01-15T10:30:00Z')
    expect(result).toContain('Jan')
    expect(result).toContain('15')
  })
})
