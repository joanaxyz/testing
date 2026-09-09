import {
  BookOpen,
  Lock,
} from 'lucide-react'

import { ChapterOverview } from '@/features/story-map/components/ChapterOverview'
import { StoryAdventurePath } from '@/features/story-map/components/path/StoryAdventurePath'
import { GamePanel } from '@/shared/components/GamePanel'
import type {
  AdventureLevelSummary,
  ChallengeSummary,
  LearningChapter,
} from '@/features/story-map/types'
import { usePlayerLoadout } from '@/shared/player-loadout/usePlayerLoadout'
import { AppTopbar } from '@/shared/navigation/AppNavigation'
import { GitCommandIcon } from '@/shared/git/commandCatalog/commandIcons'
import { DEFAULT_STORY_WORLD_SLUG, getStoryWorld } from '@/shared/story-worlds/registry'

// Fixed, runtime-computed schedule - mirrors progress.chests.CHEST_SCHEDULE.
const PREVIEW_CHEST_SCHEDULE = [
  { threshold: 25, coins: 25 },
  { threshold: 50, coins: 60 },
  { threshold: 75, coins: 100 },
  { threshold: 100, coins: 150 },
]

const PREVIEW_CHAPTERS: LearningChapter[] = [
  {
    id: 1,
    slug: 'creating-inspecting-repositories',
    number: 1,
    title: 'Foundations',
    description: 'Practice the first Git commands in the Arcane Spire.',
    sort_order: 1,
    is_orientation: false,
    is_playable: true,
    story: { id: 1, slug: 'arcane-spire', title: 'Arcane Spire', world_slug: 'arcane-spire' },
    locked: false,
    lock_reason: '',
    command_skill_count: 4,
    challenge_count: 1,
    adventure_level_count: 6,
    level_completion: { value: 64, numerator: 4, denominator: 6 },
    chest_schedule: PREVIEW_CHEST_SCHEDULE,
  },
  {
    id: 2,
    slug: 'branching',
    number: 2,
    title: 'Branching',
    description: '',
    sort_order: 2,
    is_orientation: false,
    is_playable: true,
    story: { id: 1, slug: 'arcane-spire', title: 'Arcane Spire', world_slug: 'arcane-spire' },
    locked: true,
    lock_reason: 'Clear Chapter 01.',
    command_skill_count: 3,
    challenge_count: 1,
    adventure_level_count: 6,
    level_completion: { value: 0, numerator: 0, denominator: 6 },
    chest_schedule: PREVIEW_CHEST_SCHEDULE,
  },
  {
    id: 3,
    slug: 'merging',
    number: 3,
    title: 'Merging',
    description: '',
    sort_order: 3,
    is_orientation: false,
    is_playable: true,
    story: { id: 1, slug: 'arcane-spire', title: 'Arcane Spire', world_slug: 'arcane-spire' },
    locked: true,
    lock_reason: 'Clear Chapter 02.',
    command_skill_count: 3,
    challenge_count: 1,
    adventure_level_count: 6,
    level_completion: { value: 0, numerator: 0, denominator: 6 },
    chest_schedule: PREVIEW_CHEST_SCHEDULE,
  },
]
const PREVIEW_NEXT_SKILL = { command: 'git add', level: 3, title: 'Stage and Commit' }

const PREVIEW_LEVELS: AdventureLevelSummary[] = Array.from({ length: 6 }, (_, index) => ({
  item_type: 'adventure',
  id: index + 1,
  slug: `preview-level-${index + 1}`,
  title: `Preview Level ${index + 1}`,
  description: '',
  command: index < 2 ? 'git init' : 'git add',
  locked: false,
  lock_reason: '',
  completion: index < 4
    ? {
        stars: 3,
        counted_action_total: 1,
        completed_at: '2026-08-25T00:00:00Z',
      }
    : null,
  // Keep the preview focused on the unlocked Challenge Gate while preserving
  // the mixed star state used to assess the map's visual hierarchy.
  is_passed: true,
  tiers: [],
}))

const PREVIEW_CHALLENGES: ChallengeSummary[] = [
  {
    item_type: 'challenge',
    id: 100,
    slug: 'repository-foundations-trial',
    title: 'Repository Foundations Trial',
    summary: 'Prove the chapter skills.',
    narrative: 'The gate awaits.',
    status: 'not_started',
    completed: false,
    locked: false,
    trials: [
      {
        id: 101,
        difficulty: 'easy',
        status: 'completed',
        cleared: true,
        replay_available: true,
        latest_attempt: null,
        completion: {
          stars: 2,
          counted_action_total: 2,
          completed_at: '2026-08-25T00:00:00Z',
        },
        command_budget: { min_counted_commands: 1, max_counted_commands: 4 },
      },
      {
        id: 102,
        difficulty: 'medium',
        status: 'completed',
        cleared: true,
        replay_available: true,
        latest_attempt: null,
        completion: {
          stars: 2,
          counted_action_total: 3,
          completed_at: '2026-08-25T00:00:00Z',
        },
        command_budget: { min_counted_commands: 2, max_counted_commands: 6 },
      },
      {
        id: 103,
        difficulty: 'hard',
        status: 'locked',
        cleared: false,
        replay_available: false,
        latest_attempt: null,
        completion: null,
        command_budget: { min_counted_commands: 3, max_counted_commands: 8 },
      },
    ],
  },
]

export function Component() {
  const activeChapter = PREVIEW_CHAPTERS[0]
  const { companion } = usePlayerLoadout()
  const storyWorld = getStoryWorld(DEFAULT_STORY_WORLD_SLUG)
  const companionPortrait = companion.sprites.portrait?.src ?? companion.sprites.idle?.src ?? ''
  const storyMapStyle = {
    backgroundImage: `url("${storyWorld.map?.background.src ?? '/cosmetics/story-worlds/arcane-spire/backgrounds/level-map.png'}")`,
  } as React.CSSProperties

  return (
    <div className="app-shell">
      <AppTopbar />
      <main className="app-main app-main--story-map">
        <div className="story-page-shell">
          <div className="story-map-backdrop" style={storyMapStyle} aria-hidden="true" />
          <div className="story-map-layout">
            <aside className="story-map-left" aria-label="Chapter tools">
              <ChapterOverview chapter={activeChapter} />
            </aside>

            <section className="story-map-stage" aria-label="Preview story map">
              <StoryAdventurePath
                chapter={activeChapter}
                levels={PREVIEW_LEVELS}
                challenges={PREVIEW_CHALLENGES}
                challengesLocked={false}
                loading={false}
                defaultTrialsOpen
              />
            </section>

        <aside className="story-map-right" aria-label="Story chapters and companion">
          <GamePanel as="section" eyebrow="Chapters" className="story-chapter-list-panel">
            <div className="story-chapter-list">
              {PREVIEW_CHAPTERS.map((chapter) => (
                <button
                  type="button"
                  className="story-chapter-row"
                  data-active={chapter.id === activeChapter.id}
                  disabled={chapter.locked}
                  key={chapter.id}
                >
                  <span className="story-chapter-row-number">{String(chapter.number).padStart(2, '0')}</span>
                  <span className="story-chapter-row-title">{chapter.title}</span>
                  {chapter.locked ? <Lock className="size-4" /> : <BookOpen className="size-5" />}
                </button>
              ))}
            </div>
          </GamePanel>

          <GamePanel as="section" eyebrow="Skill Reward" className="story-skill-reward-detail-panel">
            <div className="story-skill-reward">
              <span className="story-skill-portrait" aria-hidden="true">
                <GitCommandIcon command={PREVIEW_NEXT_SKILL.command} className="story-skill-portrait-glyph" />
              </span>
              <div className="story-skill-reward-copy">
                <code className="story-skill-reward-name">{PREVIEW_NEXT_SKILL.command}</code>
                <span className="story-skill-reward-level">Level {PREVIEW_NEXT_SKILL.level} Skill Reward</span>
                <p className="story-skill-reward-desc">
                  Clear <strong>{PREVIEW_NEXT_SKILL.title}</strong> to inscribe {companion.label}'s{' '}
                  <code>{PREVIEW_NEXT_SKILL.command}</code> spell.
                </p>
              </div>
            </div>
          </GamePanel>

          <GamePanel as="section" eyebrow={companion.label} title="Your Companion" className="story-companion-panel">
            <div className="story-companion-body">
              <div className="story-companion-copy">
                <dl>
                  <div>
                    <dt>Rank</dt>
                    <dd>IV</dd>
                  </div>
                  <div>
                    <dt>Next Rank</dt>
                    <dd>320 / 500 XP</dd>
                  </div>
                </dl>
              </div>
            </div>
            <img className="story-companion-portrait" src={companionPortrait} alt="" />
          </GamePanel>
        </aside>
          </div>
        </div>
      </main>
    </div>
  )
}
