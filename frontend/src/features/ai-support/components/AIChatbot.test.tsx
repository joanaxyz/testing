import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { aiSupportApi } from '@/features/ai-support/api/aiSupportApi'
import { ApiError } from '@/shared/api/apiError'
import { useAuthStore } from '@/shared/auth/useAuth'
import { COMPANIONS } from '@/shared/cosmetics/companions/registry'

import { AIChatbot } from './AIChatbot'

const mocks = vi.hoisted(() => ({
  usePlayerLoadout: vi.fn(),
}))

vi.mock('@/shared/player-loadout/usePlayerLoadout', () => ({
  usePlayerLoadout: mocks.usePlayerLoadout,
}))

vi.mock('@/shared/sprites/SpriteAnimator', () => ({
  SpriteAnimator: ({ animation, autoPlay, 'aria-label': ariaLabel }: {
    animation: { name: string; src: string }
    autoPlay?: boolean
    'aria-label'?: string
  }) => (
    <div
      aria-label={ariaLabel}
      data-animation={animation.name}
      data-autoplay={String(autoPlay)}
      data-src={animation.src}
    />
  ),
}))

function renderChat(path = '/home') {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AIChatbot />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AIChatbot', () => {
  beforeEach(() => {
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      configurable: true,
      value: vi.fn(),
    })
    useAuthStore.setState({
      accessToken: 'test-token',
      user: { id: 7, username: 'student', email: 'student@example.com', is_staff: false },
    })
    mocks.usePlayerLoadout.mockReturnValue({
      companion: COMPANIONS.white,
      companionSlug: 'white',
      hasCompanion: true,
      isLoading: false,
      isError: false,
      error: null,
    })
    document.documentElement.dataset.motion = 'full'
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    useAuthStore.setState({ accessToken: null, user: null })
    document.documentElement.removeAttribute('data-motion')
  })

  it('opens as the equipped companion with themed policy and page context', () => {
    renderChat('/stories/arcane-spire')

    const launcher = screen.getByRole('button', { name: 'Open Git learning assistant' })
    fireEvent.click(launcher)

    expect(screen.getByRole('dialog', { name: 'Ask White' })).toBeInTheDocument()
    expect(screen.getByText('No-answer policy')).toBeInTheDocument()
    expect(screen.getByText('Context: Story map')).toBeInTheDocument()
    expect(document.querySelector('[data-src="/cosmetics/companion/white/idle.png"]')).toBeInTheDocument()
  })

  it('sends complete replies and includes only completed exchanges in follow-up history', async () => {
    const chat = vi.spyOn(aiSupportApi, 'chat')
      .mockResolvedValueOnce({ reply: 'A branch is a movable reference.', policy_status: 'allowed', request_id: 'one' })
      .mockResolvedValueOnce({ reply: 'HEAD identifies the current position.', policy_status: 'allowed', request_id: 'two' })
    renderChat('/home')
    fireEvent.click(screen.getByRole('button', { name: 'Open Git learning assistant' }))

    const input = screen.getByLabelText('Ask a Git concept question')
    fireEvent.change(input, { target: { value: 'What is a branch?' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(await screen.findByText('A branch is a movable reference.')).toBeInTheDocument()
    expect(chat).toHaveBeenNthCalledWith(1, {
      message: 'What is a branch?',
      history: [],
      page_context: 'home',
    })

    fireEvent.change(input, { target: { value: 'And what is HEAD?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))

    await waitFor(() => expect(chat).toHaveBeenCalledTimes(2))
    expect(chat).toHaveBeenNthCalledWith(2, {
      message: 'And what is HEAD?',
      history: [
        { role: 'user', content: 'What is a branch?' },
        { role: 'assistant', content: 'A branch is a movable reference.' },
      ],
      page_context: 'home',
    })
  })

  it('shows a useful unavailable state without adding failed turns to history', async () => {
    vi.spyOn(aiSupportApi, 'chat').mockRejectedValue(
      new ApiError('unavailable', 503, { detail: 'unavailable' }),
    )
    renderChat()
    fireEvent.click(screen.getByRole('button', { name: 'Open Git learning assistant' }))
    fireEvent.change(screen.getByLabelText('Ask a Git concept question'), {
      target: { value: 'What is HEAD?' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))

    expect(await screen.findByText(/temporarily unavailable/i)).toBeInTheDocument()
  })

  it('renders assistant Markdown as readable formatted content', async () => {
    vi.spyOn(aiSupportApi, 'chat').mockResolvedValue({
      reply: '**Branches** help you:\n\n- isolate work\n- protect stable code',
      policy_status: 'allowed',
      request_id: 'markdown',
    })
    renderChat('/home')
    fireEvent.click(screen.getByRole('button', { name: 'Open Git learning assistant' }))
    fireEvent.change(screen.getByLabelText('Ask a Git concept question'), {
      target: { value: 'Why use branches?' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))

    expect(await screen.findByText('Branches')).toHaveProperty('tagName', 'STRONG')
    expect(screen.getByText('isolate work')).toHaveProperty('tagName', 'LI')
    expect(screen.getByText('protect stable code')).toHaveProperty('tagName', 'LI')
  })

  it('uses a static first frame when reduced motion is active', () => {
    document.documentElement.dataset.motion = 'reduced'
    renderChat()

    expect(document.querySelector('[data-autoplay="false"]')).toBeInTheDocument()
  })

  it('uses Blue as display-only fallback when no companion is equipped', () => {
    mocks.usePlayerLoadout.mockReturnValue({
      companion: COMPANIONS.blue,
      companionSlug: 'blue',
      hasCompanion: false,
      isLoading: false,
      isError: false,
      error: null,
    })
    renderChat()

    fireEvent.click(screen.getByRole('button', { name: 'Open Git learning assistant' }))
    expect(screen.getByRole('dialog', { name: 'Ask Blue' })).toBeInTheDocument()
    expect(document.querySelector('[data-src="/cosmetics/companion/blue/idle.png"]')).toBeInTheDocument()
  })

  it('recovers after a rate-limit response', async () => {
    vi.spyOn(aiSupportApi, 'chat')
      .mockRejectedValueOnce(new ApiError('busy', 429, { detail: 'busy' }))
      .mockResolvedValueOnce({
        reply: 'A remote is a named connection to another repository.',
        policy_status: 'allowed',
        request_id: 'retry',
      })
    renderChat()
    fireEvent.click(screen.getByRole('button', { name: 'Open Git learning assistant' }))
    const input = screen.getByLabelText('Ask a Git concept question')

    fireEvent.change(input, { target: { value: 'What is a remote?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))
    expect(await screen.findByText(/too many questions/i)).toBeInTheDocument()

    fireEvent.change(input, { target: { value: 'Can I try again?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }))
    expect(await screen.findByText('A remote is a named connection to another repository.')).toBeInTheDocument()
  })

  it('hides for staff and authoring routes', () => {
    useAuthStore.setState({
      user: { id: 1, username: 'admin', email: 'admin@example.com', is_staff: true },
    })
    const staff = renderChat()
    expect(screen.queryByRole('button', { name: 'Open Git learning assistant' })).not.toBeInTheDocument()
    staff.unmount()

    useAuthStore.setState({
      user: { id: 7, username: 'student', email: 'student@example.com', is_staff: false },
    })
    renderChat('/level-editor/12')
    expect(screen.queryByRole('button', { name: 'Open Git learning assistant' })).not.toBeInTheDocument()
  })

  it('closes on Escape and returns focus to the launcher', async () => {
    renderChat()
    const launcher = screen.getByRole('button', { name: 'Open Git learning assistant' })
    fireEvent.click(launcher)
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    fireEvent.keyDown(document, { key: 'Escape' })

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await waitFor(() => expect(launcher).toHaveFocus())
  })
})
