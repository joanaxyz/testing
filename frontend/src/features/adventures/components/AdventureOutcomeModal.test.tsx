import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AdventureOutcomeModal } from './AdventureOutcomeModal'
import type { AdventureRun } from '@/features/adventures/types'

const run: AdventureRun = {
  id: 1,
  status: 'completed',
  replay: false,
  stars: 3,
  library_opened: false,
  is_passed: true,
  passed: true,
  selected_level: { id: 1, slug: 'create-repository', title: 'Create a repository', is_required: true },
  next_level: null,
  chapter_id: 1,
  current_level_index: 2,
  total_levels: 2,
  current_wave: 2,
  total_waves: 2,
  mastery: {
    commands: [
      {
        slug: 'git-init/current-directory',
        form_id: 1,
        form_slug: 'current-directory',
        skill_slug: 'git-init',
        title: 'git init',
        strength: 2,
        mastered_bar: 2,
        introduced: true,
        mastered: true,
      },
      {
        slug: 'git-status/plain',
        form_id: 2,
        form_slug: 'plain',
        skill_slug: 'git-status',
        title: 'git status',
        strength: 1,
        mastered_bar: 2,
        introduced: true,
        mastered: false,
      },
    ],
    commands_mastered: 1,
    total_commands: 2,
    total_achievable: 80,
    passed: true,
  },
  story: { id: 1, slug: 'arcane-spire', title: 'The Arcane Spire', world_slug: 'arcane-spire' },
  battle_stage: null,
  completed_at: '2026-06-07T00:00:00Z',
  current_attempt: null,
  results: [],
  progress: { completed: 2, total: 2 },
}

describe('AdventureOutcomeModal', () => {
  afterEach(() => cleanup())

  it('surfaces the pass state, keeping the per-command mastery breakdown collapsed until expanded', () => {
    render(<AdventureOutcomeModal open run={run} onRestart={vi.fn()} onClose={vi.fn()} />)
    expect(screen.getByRole('dialog')).toHaveClass('game-outcome-backdrop')
    expect(screen.getByRole('img', { name: 'You Won' })).toBeInTheDocument()
    expect(screen.getByText('Challenge unlocked')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /play again/i })).toBeInTheDocument()

    const toggle = screen.getByRole('button', { name: /command mastery/i })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Mastered')).not.toBeInTheDocument()
    expect(screen.queryByText('In progress')).not.toBeInTheDocument()

    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Mastered')).toBeInTheDocument()
    expect(screen.getByText('In progress')).toBeInTheDocument()

    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Mastered')).not.toBeInTheDocument()
  })

  it('shows a next level action when the adventure has another level', () => {
    render(
      <AdventureOutcomeModal
        open
        run={{
          ...run,
          current_level_index: 1,
          progress: { completed: 1, total: 2 },
          next_level: { id: 2, slug: 'first-commit', title: 'First commit', is_required: true },
        }}
        onRestart={vi.fn()}
        onNextLevel={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /next level/i })).toBeInTheDocument()
  })

  it('promotes retry when a winning run is below a perfect score', () => {
    render(
      <AdventureOutcomeModal
        open
        run={{
          ...run,
          stars: 2,
          library_opened: true,
          next_level: { id: 2, slug: 'first-commit', title: 'First commit', is_required: true },
        }}
        onRestart={vi.fn()}
        onNextLevel={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByText('Library used')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^retry$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /next level/i })).toBeInTheDocument()
  })

  it('frames a replay as uncounted free-play instead of a pass', () => {
    render(
      <AdventureOutcomeModal
        open
        run={{ ...run, replay: true, mastery: { ...run.mastery, passed: false } }}
        onRestart={vi.fn()}
        onClose={vi.fn()}
      />,
    )
    expect(screen.getByText('Free play')).toBeInTheDocument()
    expect(screen.queryByText('Challenge unlocked')).not.toBeInTheDocument()
  })

  it('renders a failed replay as game over, not a success celebration', () => {
    render(
      <AdventureOutcomeModal
        open
        run={{ ...run, replay: true, status: 'failed', stars: 0, mastery: { ...run.mastery, passed: false } }}
        onRestart={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByRole('img', { name: 'Game Over' })).toBeInTheDocument()
    expect(screen.getByText('Replay failed')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: 'You Won' })).not.toBeInTheDocument()
  })

  it('treats an incomplete counted adventure as game over instead of run ended', () => {
    render(
      <AdventureOutcomeModal
        open
        run={{ ...run, stars: 1, mastery: { ...run.mastery, passed: false } }}
        onRestart={vi.fn()}
        onClose={vi.fn()}
      />,
    )

    expect(screen.getByRole('img', { name: 'Game Over' })).toBeInTheDocument()
    expect(screen.getByText('Adventure failed')).toBeInTheDocument()
    expect(screen.queryByText(/run ended/i)).not.toBeInTheDocument()
  })
})
