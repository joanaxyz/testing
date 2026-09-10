import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { Sparkles } from 'lucide-react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { GameOutcomeModal } from './GameOutcomeModal'

describe('GameOutcomeModal', () => {
  afterEach(() => {
    delete document.documentElement.dataset.motion
    cleanup()
  })

  it('lands a staggered burst under each earned star when motion is full', async () => {
    document.documentElement.dataset.motion = 'full'

    render(
      <GameOutcomeModal
        open
        onClose={vi.fn()}
        title="Level complete"
        tone="success"
        icon={Sparkles}
        stars={2}
        headline="Adventure cleared"
        message="Nice work."
      />,
    )

    await waitFor(() => expect(screen.getByRole('img', { name: '2 of 3 stars earned' })).toBeInTheDocument())

    const bursts = document.querySelectorAll('.game-outcome-star-burst')
    expect(bursts).toHaveLength(2)
  })

  it('skips the star-burst layer entirely when motion is reduced', async () => {
    document.documentElement.dataset.motion = 'reduced'

    render(
      <GameOutcomeModal
        open
        onClose={vi.fn()}
        title="Level complete"
        tone="success"
        icon={Sparkles}
        stars={3}
        headline="Adventure cleared"
        message="Nice work."
      />,
    )

    await waitFor(() => expect(screen.getByRole('img', { name: '3 of 3 stars earned' })).toBeInTheDocument())

    expect(document.querySelectorAll('.game-outcome-star-burst')).toHaveLength(0)
  })
})
