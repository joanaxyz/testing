import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { performanceApi } from '@/features/performance/api/performanceApi'
import type { PerformanceSummary } from '@/features/performance/types'
import { PerformancePage } from './PerformancePage'

const summary: PerformanceSummary = {
  completed_sessions: 14,
  kpis: {
    scr: { value: 40, numerator: 14, denominator: 35 },
    car: { value: 100, numerator: 42, denominator: 42 },
    hlcr: { value: 0, numerator: 0, denominator: 3 },
    rtr: { value: 40, numerator: 2, denominator: 5 },
    arc: { value: 1.43, numerator: 20, denominator: 14 },
  },
  modules: [
    {
      number: 0,
      title: 'Module 0',
      scr: { value: null, numerator: 0, denominator: 0 },
      hlcr: { value: null, numerator: 0, denominator: 0 },
      rtr: { value: null, numerator: 0, denominator: 0 },
      arc: { value: null, numerator: 0, denominator: 0 },
    },
    {
      number: 1,
      title: 'Module 1',
      scr: { value: 0, numerator: 0, denominator: 1 },
      hlcr: { value: null, numerator: 0, denominator: 0 },
      rtr: { value: null, numerator: 0, denominator: 0 },
      arc: { value: null, numerator: 0, denominator: 0 },
    },
  ],
}

describe('PerformancePage', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders server-owned KPIs and empty module states', async () => {
    vi.spyOn(performanceApi, 'summary').mockResolvedValue(summary)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter><PerformancePage /></MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByRole('heading', { name: 'Performance' })).toBeInTheDocument()
    expect(screen.getByText('14/35 attempts')).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
    expect(screen.getAllByText('1.43')).toHaveLength(2)
    expect(screen.queryByText('Module 0')).not.toBeInTheDocument()
    expect(screen.getByText('Module 1')).toBeInTheDocument()
    expect(screen.getAllByText('Waiting for practice')).toHaveLength(3)
  })
})
