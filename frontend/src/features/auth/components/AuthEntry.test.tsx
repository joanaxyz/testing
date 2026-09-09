import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { authApi } from '@/shared/auth/authApi'
import { useAuthStore } from '@/shared/auth/useAuth'
import { LoginForm } from './LoginForm'
import { RegisterForm } from './RegisterForm'

const session = {
  access: 'test-access',
  user: { id: 11, username: 'archivist', email: 'archivist@example.test', is_staff: false },
}
let client: QueryClient

function renderEntry(register = false) {
  client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[register ? '/register' : '/login']}>
        <Routes>
          <Route path="/register" element={<RegisterForm />} />
          <Route path="/login" element={<LoginForm />} />
          <Route path="/stories/git-it-legacy" element={<h1>Story map</h1>} />
          <Route path="/home" element={<h1>Home</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function fillRegistration() {
  fireEvent.change(screen.getByPlaceholderText('Username'), { target: { value: 'archivist' } })
  fireEvent.change(screen.getByPlaceholderText('Email'), { target: { value: 'archivist@example.test' } })
  fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'safe-password-123' } })
  fireEvent.change(screen.getByPlaceholderText('Confirm password'), { target: { value: 'safe-password-123' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
}

describe('authentication entry destination', () => {
  beforeEach(() => {
    vi.spyOn(authApi, 'login').mockResolvedValue(session)
    vi.spyOn(authApi, 'register').mockResolvedValue({ user: session.user })
  })
  afterEach(() => {
    cleanup()
    client.clear()
    useAuthStore.setState({ accessToken: null, user: null })
    vi.restoreAllMocks()
  })

  it('opens Stories after signing in', async () => {
    renderEntry()
    fireEvent.change(screen.getByPlaceholderText('Username or email'), { target: { value: 'archivist' } })
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'safe-password-123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('heading', { name: 'Story map' })).toBeInTheDocument()
    expect(useAuthStore.getState().user?.id).toBe(11)
  })

  it('opens Stories immediately after creating an account', async () => {
    renderEntry(true)
    fillRegistration()
    expect(await screen.findByRole('heading', { name: 'Story map' })).toBeInTheDocument()
    expect(authApi.register).toHaveBeenCalledOnce()
  })

  it('still offers sign-in if the account was created but automatic login failed', async () => {
    vi.mocked(authApi.login).mockRejectedValue(new Error('Temporarily unavailable'))
    renderEntry(true)
    fillRegistration()
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Story map' })).not.toBeInTheDocument()
  })
})
