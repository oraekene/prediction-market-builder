import { describe, it, expect } from 'vitest'
import { NODE_TYPE_REGISTRY, getNodeType, getBackendType, getDefaultConfig } from './nodeTypeRegistry'

describe('NODE_TYPE_REGISTRY', () => {
  it('contains expected node categories', () => {
    const entries = Object.values(NODE_TYPE_REGISTRY)
    const categories = [...new Set(entries.map(n => n.category))]
    expect(categories).toContain('Sources')
    expect(categories).toContain('Actions')
    expect(categories).toContain('Conditions')
    expect(categories).toContain('Performance')
  })

  it('each entry has required fields', () => {
    const entries = Object.values(NODE_TYPE_REGISTRY)
    for (const entry of entries) {
      expect(entry.label).toBeTruthy()
      expect(entry.backendType).toBeTruthy()
      expect(entry.category).toBeTruthy()
      expect(entry.color).toBeTruthy()
      expect(entry.defaultConfig).toBeDefined()
      expect(entry.description).toBeTruthy()
    }
  })
})

describe('getNodeType', () => {
  it('returns node type definition by label', () => {
    const entry = getNodeType('Polymarket')
    expect(entry).toBeDefined()
    expect(entry?.category).toBe('Sources')
  })

  it('returns undefined for unknown label', () => {
    expect(getNodeType('nonexistent')).toBeUndefined()
  })
})

describe('getBackendType', () => {
  it('maps node label to backend type', () => {
    expect(getBackendType('Polymarket')).toBe('polymarket_source')
    expect(getBackendType('Stop-Loss')).toBe('stop_loss')
  })

  it('returns unknown for unknown label', () => {
    expect(getBackendType('nonexistent')).toBe('unknown')
  })
})

describe('getDefaultConfig', () => {
  it('returns default config for known node', () => {
    const config = getDefaultConfig('Threshold')
    expect(config).toEqual({ field: 'current_odds', operator: 'lt', threshold: 0.5 })
  })

  it('returns empty object for unknown label', () => {
    expect(getDefaultConfig('nonexistent')).toEqual({})
  })
})
