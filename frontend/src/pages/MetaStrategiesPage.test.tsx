import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import MetaStrategiesPage from './MetaStrategiesPage'

vi.mock('@/components/meta-strategies/MetaStrategyList', () => ({
  default: () => <div>Meta Strategy List</div>,
}))

vi.mock('@/components/meta-strategies/MetaStrategyDetail', () => ({
  default: () => <div>Meta Strategy Detail</div>,
}))

function createWrapper(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return function Wrapper() {
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/meta-strategies" element={<MetaStrategiesPage />} />
            <Route path="/meta-strategies/:id" element={<MetaStrategiesPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
}

describe('MetaStrategiesPage', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('renders list view when no id param', () => {
    render(<MetaStrategiesPage />, { wrapper: createWrapper('/meta-strategies') })
    expect(screen.getByText('Meta Strategy List')).toBeInTheDocument()
  })

  it('renders detail view when id param is present', () => {
    render(<MetaStrategiesPage />, { wrapper: createWrapper('/meta-strategies/meta-1') })
    expect(screen.getByText('Meta Strategy Detail')).toBeInTheDocument()
  })
})
