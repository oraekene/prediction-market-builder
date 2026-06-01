import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import {
  useStrategies, useStrategy, useCreateStrategy, useUpdateStrategy, useDeleteStrategy,
  useDeployStrategy, usePauseStrategy, useResumeStrategy, useArchiveStrategy,
  useRollbackStrategy, useStrategyHistory, useEvaluateStrategyData,
  useStrategyTemplates, useStrategyTemplate, useCreateStrategyTemplate,
  useUpdateStrategyTemplate, useDeleteStrategyTemplate, useApplyStrategyTemplate,
} from './useStrategies'
import { createMockStrategy, createMockStrategies } from '@/test/mocks'

const mockFetchStrategies = vi.fn()
const mockFetchStrategy = vi.fn()
const mockCreateStrategy = vi.fn()
const mockUpdateStrategy = vi.fn()
const mockDeleteStrategy = vi.fn()
const mockDeployStrategy = vi.fn()
const mockPauseStrategy = vi.fn()
const mockResumeStrategy = vi.fn()
const mockArchiveStrategy = vi.fn()
const mockRollbackStrategy = vi.fn()
const mockFetchStrategyHistory = vi.fn()
const mockEvaluateStrategyData = vi.fn()
const mockFetchStrategyTemplates = vi.fn()
const mockCreateStrategyTemplate = vi.fn()
const mockFetchStrategyTemplate = vi.fn()
const mockUpdateStrategyTemplate = vi.fn()
const mockDeleteStrategyTemplate = vi.fn()
const mockApplyStrategyTemplate = vi.fn()

vi.mock('@/lib/api', () => ({
  fetchStrategies: (...args: any[]) => mockFetchStrategies(...args),
  fetchStrategy: (...args: any[]) => mockFetchStrategy(...args),
  createStrategy: (...args: any[]) => mockCreateStrategy(...args),
  updateStrategy: (...args: any[]) => mockUpdateStrategy(...args),
  deleteStrategy: (...args: any[]) => mockDeleteStrategy(...args),
  deployStrategy: (...args: any[]) => mockDeployStrategy(...args),
  pauseStrategy: (...args: any[]) => mockPauseStrategy(...args),
  resumeStrategy: (...args: any[]) => mockResumeStrategy(...args),
  archiveStrategy: (...args: any[]) => mockArchiveStrategy(...args),
  rollbackStrategy: (...args: any[]) => mockRollbackStrategy(...args),
  fetchStrategyHistory: (...args: any[]) => mockFetchStrategyHistory(...args),
  evaluateStrategyData: (...args: any[]) => mockEvaluateStrategyData(...args),
  fetchStrategyTemplates: (...args: any[]) => mockFetchStrategyTemplates(...args),
  createStrategyTemplate: (...args: any[]) => mockCreateStrategyTemplate(...args),
  fetchStrategyTemplate: (...args: any[]) => mockFetchStrategyTemplate(...args),
  updateStrategyTemplate: (...args: any[]) => mockUpdateStrategyTemplate(...args),
  deleteStrategyTemplate: (...args: any[]) => mockDeleteStrategyTemplate(...args),
  applyStrategyTemplate: (...args: any[]) => mockApplyStrategyTemplate(...args),
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('useStrategies', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns strategies list', async () => {
    const strategies = createMockStrategies(3)
    mockFetchStrategies.mockResolvedValue(strategies)
    const { result } = renderHook(() => useStrategies(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(strategies)
  })
})

describe('useStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns a single strategy', async () => {
    const strategy = createMockStrategy()
    mockFetchStrategy.mockResolvedValue(strategy)
    const { result } = renderHook(() => useStrategy('strategy-1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual(strategy)
  })

  it('is disabled when id is empty', () => {
    const { result } = renderHook(() => useStrategy(''), { wrapper: createWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useCreateStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls createStrategy on mutation', async () => {
    const newStrategy = createMockStrategy()
    mockCreateStrategy.mockResolvedValue(newStrategy)
    const { result } = renderHook(() => useCreateStrategy(), { wrapper: createWrapper() })
    result.current.mutate(newStrategy)
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockCreateStrategy).toHaveBeenCalledWith(newStrategy, expect.any(Object))
  })
})

describe('useUpdateStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls updateStrategy on mutation', async () => {
    mockUpdateStrategy.mockResolvedValue(undefined)
    const { result } = renderHook(() => useUpdateStrategy(), { wrapper: createWrapper() })
    result.current.mutate({ id: 'strategy-1', data: { name: 'Updated' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockUpdateStrategy).toHaveBeenCalledWith('strategy-1', { name: 'Updated' })
  })
})

describe('useDeployStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls deployStrategy on mutation', async () => {
    mockDeployStrategy.mockResolvedValue({ status: 'active' })
    const { result } = renderHook(() => useDeployStrategy(), { wrapper: createWrapper() })
    result.current.mutate('s1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockDeployStrategy).toHaveBeenCalledWith('s1', expect.any(Object))
  })
})

describe('usePauseStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls pauseStrategy on mutation', async () => {
    mockPauseStrategy.mockResolvedValue({ status: 'paused' })
    const { result } = renderHook(() => usePauseStrategy(), { wrapper: createWrapper() })
    result.current.mutate('s1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockPauseStrategy).toHaveBeenCalledWith('s1', expect.any(Object))
  })
})

describe('useResumeStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls resumeStrategy on mutation', async () => {
    mockResumeStrategy.mockResolvedValue({ status: 'active' })
    const { result } = renderHook(() => useResumeStrategy(), { wrapper: createWrapper() })
    result.current.mutate('s1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockResumeStrategy).toHaveBeenCalledWith('s1', expect.any(Object))
  })
})

describe('useArchiveStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls archiveStrategy on mutation', async () => {
    mockArchiveStrategy.mockResolvedValue({ status: 'archived' })
    const { result } = renderHook(() => useArchiveStrategy(), { wrapper: createWrapper() })
    result.current.mutate('s1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockArchiveStrategy).toHaveBeenCalledWith('s1', expect.any(Object))
  })
})

describe('useRollbackStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls rollbackStrategy on mutation', async () => {
    mockRollbackStrategy.mockResolvedValue({ version: 2 })
    const { result } = renderHook(() => useRollbackStrategy(), { wrapper: createWrapper() })
    result.current.mutate('s1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockRollbackStrategy).toHaveBeenCalledWith('s1', expect.any(Object))
  })
})

describe('useStrategyHistory', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns strategy history', async () => {
    mockFetchStrategyHistory.mockResolvedValue({ current_version: 2, history: [] })
    const { result } = renderHook(() => useStrategyHistory('s1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual({ current_version: 2, history: [] })
  })

  it('is disabled when id is empty', () => {
    const { result } = renderHook(() => useStrategyHistory(''), { wrapper: createWrapper() })
    expect(result.current.fetchStatus).toBe('idle')
  })
})

describe('useEvaluateStrategyData', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls evaluateStrategyData on mutation', async () => {
    mockEvaluateStrategyData.mockResolvedValue({ result: 'ok' })
    const { result } = renderHook(() => useEvaluateStrategyData(), { wrapper: createWrapper() })
    result.current.mutate({ nodes: [], edges: [] })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockEvaluateStrategyData).toHaveBeenCalledWith({ nodes: [], edges: [] }, expect.any(Object))
  })
})

describe('useStrategyTemplates', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns templates list', async () => {
    mockFetchStrategyTemplates.mockResolvedValue([{ id: 't1', name: 'Test' }])
    const { result } = renderHook(() => useStrategyTemplates(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([{ id: 't1', name: 'Test' }])
  })
})

describe('useStrategyTemplate', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('returns a single template', async () => {
    mockFetchStrategyTemplate.mockResolvedValue({ id: 't1', name: 'Test' })
    const { result } = renderHook(() => useStrategyTemplate('t1'), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual({ id: 't1', name: 'Test' })
  })
})

describe('useCreateStrategyTemplate', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls createStrategyTemplate on mutation', async () => {
    mockCreateStrategyTemplate.mockResolvedValue({ id: 't1' })
    const { result } = renderHook(() => useCreateStrategyTemplate(), { wrapper: createWrapper() })
    result.current.mutate({ name: 'test', config: {} })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockCreateStrategyTemplate).toHaveBeenCalledWith({ name: 'test', config: {} }, expect.any(Object))
  })
})

describe('useUpdateStrategyTemplate', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls updateStrategyTemplate on mutation', async () => {
    mockUpdateStrategyTemplate.mockResolvedValue({})
    const { result } = renderHook(() => useUpdateStrategyTemplate(), { wrapper: createWrapper() })
    result.current.mutate({ id: 't1', data: { name: 'new' } })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockUpdateStrategyTemplate).toHaveBeenCalledWith('t1', { name: 'new' })
  })
})

describe('useDeleteStrategyTemplate', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls deleteStrategyTemplate on mutation', async () => {
    mockDeleteStrategyTemplate.mockResolvedValue({})
    const { result } = renderHook(() => useDeleteStrategyTemplate(), { wrapper: createWrapper() })
    result.current.mutate('t1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockDeleteStrategyTemplate).toHaveBeenCalledWith('t1', expect.any(Object))
  })
})

describe('useApplyStrategyTemplate', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls applyStrategyTemplate on mutation', async () => {
    mockApplyStrategyTemplate.mockResolvedValue({ id: 's1' })
    const { result } = renderHook(() => useApplyStrategyTemplate(), { wrapper: createWrapper() })
    result.current.mutate('t1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockApplyStrategyTemplate).toHaveBeenCalledWith('t1', expect.any(Object))
  })
})

describe('useDeleteStrategy', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('calls deleteStrategy on mutation', async () => {
    mockDeleteStrategy.mockResolvedValue(undefined)
    const { result } = renderHook(() => useDeleteStrategy(), { wrapper: createWrapper() })
    result.current.mutate('strategy-1')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockDeleteStrategy).toHaveBeenCalledWith('strategy-1', expect.any(Object))
  })
})
