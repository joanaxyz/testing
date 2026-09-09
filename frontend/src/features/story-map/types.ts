import type { ChallengeStatus, ChallengeTrialAccess } from '@/features/challenges/types'
import type { BookPage } from '@/features/story-map/components/book/bookTypes'
import type { ApiSchemas } from '@/shared/api/generated/apiTypes'

type LevelCompletionSummary = {
  stars: number
  counted_action_total: number
  completed_at: string
}

export type AdventureLevelTierAccess = {
  id: number
  difficulty: 'easy' | 'medium' | 'hard'
  locked: boolean
  wave_progress: { completed: number; total: number }
  completion: LevelCompletionSummary | null
}

type AdventureSummary = {
  item_type: 'adventure'
  id: number
  slug: string
  title: string
  description: string
  command: string
  locked: boolean
  lock_reason: string
  completion: LevelCompletionSummary | null
  // Stable across re-runs: true once the level has ever been passed. Drives
  // the challenge gate and progress so a post-pass replay can't relock anything.
  is_passed: boolean
  // Per-difficulty tiers for levels ported from the old Module 1-4 scenario
  // system. Empty for every existing arcane-spire level (single-wave flow) -
  // StoryAdventurePath falls back to the plain Play pill in that case.
  tiers: AdventureLevelTierAccess[]
}

export type AdventureLevelSummary = AdventureSummary

export type ChallengeSummary = {
  item_type: 'challenge'
  id: number
  slug: string
  title: string
  summary: string
  narrative: string
  status: ChallengeStatus
  completed: boolean
  locked: boolean
  trials: ChallengeTrialAccess[]
}

type ChapterLessonSummary = {
  item_type: 'lesson'
  id: number
  slug: string
  title: string
  summary: string
  // Pages ship inline (lessons are small), so opening the reader needs no fetch.
  pages: BookPage[]
}

export type ChapterContentOverview = {
  chapter_id: number
  adventures: AdventureSummary[]
  lessons: ChapterLessonSummary[]
  challenges: ChallengeSummary[]
}

export type Story = ApiSchemas['Story']

export type LearningChapter = ApiSchemas['ChapterList']
