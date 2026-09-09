import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import type { AdventureLevelSummary } from '@/features/story-map/types'

import { StoryCompanionPanel, StorySkillFocusPanel } from './StorySidePanels'

vi.mock('@/shared/progress/rank', () => ({
  useRank: () => null,
}))

const firstLevel: AdventureLevelSummary = {
  item_type: 'adventure',
  id: 1,
  slug: 'start-a-repository',
  title: 'Start a Repository',
  description: '',
  command: 'git init',
  locked: false,
  lock_reason: '',
  completion: null,
  is_passed: false,
  tiers: [],
}

afterEach(cleanup)

describe('Story side-panel companion state', () => {
  it('shows an explicit acquisition path instead of projecting the Blue fallback', () => {
    render(
      <MemoryRouter>
        <StorySkillFocusPanel
          levels={[firstLevel]}
          companionSlug={null}
          companionLabel={null}
          loading={false}
        />
        <StoryCompanionPanel companion={null} />
      </MemoryRouter>,
    )

    expect(screen.getByText('No Companion Selected')).toBeInTheDocument()
    expect(screen.queryByText(/blue/i)).not.toBeInTheDocument()
    const links = screen.getAllByRole('link', { name: /choose (?:a )?companion/i })
    expect(links).toHaveLength(2)
    links.forEach((link) => {
      expect(link).toHaveAttribute('href', '/shop?tab=companions&required=1')
    })
    expect(screen.getByText(/before clearing/i)).toBeInTheDocument()
  })
})
