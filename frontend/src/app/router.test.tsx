import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/shared/auth/useAuth'
import { router } from './router'

vi.mock('@/app/layouts/HomeLayout', async () => {
  const { Outlet } = await import('react-router-dom')
  return { HomeLayout: () => <Outlet /> }
})
vi.mock('@/features/home/pages/HomePage', () => ({ HomePage: () => <h1>Home</h1> }))
vi.mock('@/features/story-map/pages/StoryMapPage', () => ({ StoryMapPage: () => <h1>Story map</h1> }))
vi.mock('@/features/performance/pages/PerformancePage', () => ({ PerformancePage: () => <h1>Performance</h1> }))

describe('app entry routing', () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  afterEach(() => {
    cleanup()
    client.clear()
    useAuthStore.setState({ accessToken: null, user: null })
  })

  it.each([
    ['/', 'Story map', '/stories/git-it-legacy'],
    ['/home', 'Home', '/home'],
    ['/performance', 'Performance', '/performance'],
  ])('opens %s at the correct destination', async (entry, title, expectedPath) => {
    useAuthStore.setState({
      accessToken: 'test-token',
      user: { id: 13, username: 'archivist', email: 'archivist@example.test', is_staff: false },
    })
    await router.navigate(entry)
    render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
    expect(await screen.findByRole('heading', { name: title })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe(expectedPath)
  })
})
