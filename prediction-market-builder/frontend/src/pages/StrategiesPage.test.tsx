import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import StrategiesPage from './StrategiesPage'

vi.mock('@/hooks/useStrategies', () => ({
  useStrategies: () => ({ data: [{ id: 's1', name: 'Test Strategy', status: 'active', mode: 'paper' }], isLoading: false }),
  useStrategy: (id: string) => ({
    data: id ? { id: 's1', name: 'Test Strategy', status: 'active', mode: 'paper', nodes: [], edges: [] } : undefined,
    isLoading: false,
  }),
  useCreateStrategy: () => ({ mutate: vi.fn() }),
  useUpdateStrategy: () => ({ mutate: vi.fn() }),
  useDeleteStrategy: () => ({ mutate: vi.fn() }),
}))

vi.mock('@/components/strategies/StrategyList', () => ({
  default: ({ onEditStrategy }: any) => (
    <div>
      <div>Strategy List</div>
      <button onClick={() => onEditStrategy('s1')}>Edit Strategy</button>
    </div>
  ),
}))

vi.mock('@/components/strategies/NodeCanvas', () => ({
  default: ({ initialNodes, onSave, onNodeSelect }: any) => (
    <div>
      <div>Node Canvas</div>
      <button onClick={() => onSave([], [])}>Save</button>
      <button onClick={() => onNodeSelect({ id: 'n1', data: {} })}>Select Node</button>
    </div>
  ),
  NodeCanvasNode: {} as any,
}))

vi.mock('@/components/strategies/NodePalette', () => ({
  default: () => <div>Node Palette</div>,
}))

vi.mock('@/components/strategies/NodePropertyPanel', () => ({
  default: ({ selectedNode }: any) => <div>Node Property Panel{selectedNode ? ` - ${selectedNode.id}` : ''}</div>,
}))

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>
  }
}

function renderPage() {
  return render(<StrategiesPage />, { wrapper: createWrapper() })
}

describe('StrategiesPage', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders list view by default', () => {
    renderPage()
    expect(screen.getByText('Strategies')).toBeInTheDocument()
    expect(screen.getByText('Strategy List')).toBeInTheDocument()
    expect(screen.getByText('Create Strategy')).toBeInTheDocument()
  })

  it('switches to canvas view on Create Strategy', async () => {
    renderPage()
    await userEvent.click(screen.getByText('Create Strategy'))
    expect(screen.getByText('New Strategy')).toBeInTheDocument()
    expect(screen.getByText('Node Canvas')).toBeInTheDocument()
    expect(screen.getByText('Node Palette')).toBeInTheDocument()
    expect(screen.getByText('Node Property Panel')).toBeInTheDocument()
    expect(screen.getByText('← Back')).toBeInTheDocument()
  })

  it('switches to canvas view on Edit Strategy', async () => {
    renderPage()
    await userEvent.click(screen.getByText('Edit Strategy'))
    expect(screen.getByText('Test Strategy')).toBeInTheDocument()
    expect(screen.getByText('active')).toBeInTheDocument()
  })

  it('returns to list view on Back', async () => {
    renderPage()
    await userEvent.click(screen.getByText('Create Strategy'))
    await userEvent.click(screen.getByText('← Back'))
    expect(screen.getByText('Strategies')).toBeInTheDocument()
    expect(screen.queryByText('Node Canvas')).not.toBeInTheDocument()
  })
})
