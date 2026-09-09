import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { emptyHomeFixture, richHomeFixture } from '@/features/home/preview/fixtures'
import type { HomeSummary } from '@/features/home/types'
import { emptyStatsFixture, richStatsFixture } from '@/features/stats/preview/fixtures'
import type { StatsSummary } from '@/features/stats/types'

import { HomeStatsView } from './HomeStatsView'

function renderView(
  home: HomeSummary = richHomeFixture,
  stats: StatsSummary = richStatsFixture,
  companionRequired = false,
) {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: <HomeStatsView home={home} stats={stats} companionRequired={companionRequired} />,
      },
    ],
    { initialEntries: ['/'] },
  )

  return render(<RouterProvider router={router} />)
}

function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value)
    Object.values(value).forEach(deepFreeze)
  }
  return value
}

function dashboard() {
  return screen.getByRole('region', { name: 'Stats overview' })
}

function gallery() {
  return screen.getByRole('region', { name: 'Achievement gallery' })
}

afterEach(cleanup)

describe('HomeStatsView contract', () => {
  it('renders the rich dashboard and exact Continue story destination', () => {
    renderView()

    expect(screen.getByRole('link', { name: /continue story/i })).toHaveAttribute('href', '/stories/git-it-legacy')

    const statsPanel = dashboard()
    const skillRows = statsPanel.querySelectorAll('.home-overview-command-row')
    expect(skillRows).toHaveLength(12)
    expect(within(statsPanel).getByLabelText('Initialize: 100%')).toBeInTheDocument()
    expect(within(statsPanel).getByLabelText('Rebase: 0%')).toBeInTheDocument()
    expect(within(statsPanel).getByLabelText('Overall mastery 60%')).toBeInTheDocument()
    expect(within(statsPanel).getByLabelText('2 of 3 proficiency stars')).toBeInTheDocument()

    const heatmap = within(statsPanel).getByRole('img', { name: 'Activity over the last 14 days' })
    expect(Array.from(heatmap.querySelectorAll('.home-overview-heatmap > span')).map((cell) => cell.getAttribute('data-level'))).toEqual([
      '2', '1', '3', '2', '1', '4', '2', '3', '2', '4', '2', '4', '3', '3',
    ])

    const story = statsPanel.querySelector('.home-overview-story-block')
    expect(story).not.toBeNull()
    expect(Array.from(story!.querySelectorAll('dd')).map((value) => value.textContent)).toEqual(['43', '26', '4'])
    expect(within(story as HTMLElement).getByLabelText('Finish rate 76%')).toBeInTheDocument()

    const kpis = statsPanel.querySelector('.home-overview-kpi-row')
    expect(kpis).not.toBeNull()
    expect(Array.from(kpis!.querySelectorAll(':scope > div > strong')).map((value) => value.textContent)).toEqual([
      '83%', '62%', '1.60', '91%',
    ])
  })

  it('routes a companion-less account directly to the required first step', () => {
    renderView(emptyHomeFixture, emptyStatsFixture, true)

    expect(screen.getByRole('heading', { name: 'Choose your first companion' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /choose companion/i })).toHaveAttribute(
      'href',
      '/shop?tab=companions&required=1',
    )
    expect(screen.queryByText(/return to the story map/i)).not.toBeInTheDocument()
  })

  it('filters the rich achievement ledger before applying the eight-card display limit', () => {
    renderView()

    const achievementGallery = gallery()
    expect(within(achievementGallery).getByText('16')).toBeInTheDocument()
    expect(within(achievementGallery).getByText('/ 19 unlocked')).toBeInTheDocument()
    expect(within(achievementGallery).getByText('325')).toBeInTheDocument()
    expect(within(achievementGallery).getByText('/ 435 pts')).toBeInTheDocument()

    const all = within(achievementGallery).getByRole('button', { name: 'All' })
    const unlocked = within(achievementGallery).getByRole('button', { name: 'Unlocked' })
    const locked = within(achievementGallery).getByRole('button', { name: 'Locked' })
    expect(all).toHaveAttribute('aria-pressed', 'true')
    expect(achievementGallery.querySelectorAll('.home-overview-achievement-card')).toHaveLength(8)
    expect(achievementGallery.querySelectorAll('.home-overview-achievement-card.is-unlocked')).toHaveLength(7)
    expect(achievementGallery.querySelectorAll('.home-overview-achievement-card.is-locked')).toHaveLength(1)

    fireEvent.click(unlocked)
    expect(unlocked).toHaveAttribute('aria-pressed', 'true')
    expect(achievementGallery.querySelectorAll('.home-overview-achievement-card')).toHaveLength(8)
    expect(achievementGallery.querySelectorAll('.home-overview-achievement-card.is-locked')).toHaveLength(0)

    fireEvent.click(locked)
    expect(locked).toHaveAttribute('aria-pressed', 'true')
    expect(achievementGallery.querySelectorAll('.home-overview-achievement-card')).toHaveLength(3)
    expect(achievementGallery.querySelectorAll('.home-overview-achievement-card.is-locked')).toHaveLength(3)
  })

  it('resets the achievement filter after the overview unmounts and remounts', () => {
    const first = renderView()
    fireEvent.click(within(gallery()).getByRole('button', { name: 'Locked' }))
    expect(within(gallery()).getByRole('button', { name: 'Locked' })).toHaveAttribute('aria-pressed', 'true')
    first.unmount()

    renderView()
    expect(within(gallery()).getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'true')
    expect(gallery().querySelectorAll('.home-overview-achievement-card')).toHaveLength(8)
  })

  it('preserves the empty-account fallbacks', () => {
    renderView(emptyHomeFixture, emptyStatsFixture)

    const statsPanel = dashboard()
    const skillRows = statsPanel.querySelectorAll('.home-overview-command-row')
    expect(skillRows).toHaveLength(12)
    expect(Array.from(skillRows).map((row) => row.lastElementChild?.textContent)).toEqual(Array(12).fill('--'))
    expect(within(statsPanel).getByLabelText('Overall mastery 0%')).toBeInTheDocument()

    const heatmap = within(statsPanel).getByRole('img', { name: 'Activity over the last 14 days' })
    expect(heatmap.querySelectorAll('.home-overview-heatmap > span')).toHaveLength(14)
    expect(Array.from(heatmap.querySelectorAll('.home-overview-heatmap > span')).every((cell) => cell.getAttribute('data-level') === '0')).toBe(true)

    const story = statsPanel.querySelector('.home-overview-story-block')
    expect(Array.from(story!.querySelectorAll('dd')).map((value) => value.textContent)).toEqual(['0', '0', '0'])
    expect(within(story as HTMLElement).getByLabelText('Finish rate 0%')).toBeInTheDocument()

    const kpis = statsPanel.querySelector('.home-overview-kpi-row')
    expect(Array.from(kpis!.querySelectorAll(':scope > div > strong')).map((value) => value.textContent)).toEqual([
      '--', '--', '--', '--',
    ])
    expect(within(gallery()).getByText('/ 19 unlocked')).toBeInTheDocument()
  })

  it('keeps story precedence and the 100-command accuracy threshold exact', () => {
    const home = structuredClone(richHomeFixture)
    const stats = structuredClone(richStatsFixture)
    stats.headline.levels_completed = 0
    stats.headline.perfect_clears = 30
    stats.headline.commands_run = 99
    stats.headline.accuracy = 95

    const first = renderView(home, stats)
    const story = dashboard().querySelector('.home-overview-story-block')
    expect(Array.from(story!.querySelectorAll('dd')).map((value) => value.textContent)).toEqual(['43', '30', '4'])
    expect(Array.from(dashboard().querySelectorAll('.home-overview-kpi-row > div > strong')).at(-1)).toHaveTextContent('--')
    first.unmount()

    stats.headline.commands_run = 100
    renderView(home, stats)
    expect(Array.from(dashboard().querySelectorAll('.home-overview-kpi-row > div > strong')).at(-1)).toHaveTextContent('95%')
  })

  it('does not mutate frozen input summaries', () => {
    const home = deepFreeze(structuredClone(richHomeFixture))
    const stats = deepFreeze(structuredClone(richStatsFixture))

    expect(() => renderView(home, stats)).not.toThrow()
  })
})
