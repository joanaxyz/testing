import type { ApiSchemas } from '@/shared/api/generated/apiTypes'
import type { RepositorySnapshot } from '@/shared/level/types'

// Ported from the archived Module 0 orientation workspace
// (archive/may30-old-modules: frontend/src/features/modules/orientation/types.ts).
// Session-only types (OrientationLessonSession, OrientationCommandResult) are
// dropped: this is read-only step-through content, no live terminal/session.

export type OrientationLayout =
  | 'storyboard'
  | 'guide_terminal'
  | 'explorer_shell'
  | 'pipeline_status'
  | 'anatomy'
  | 'dag_log'
  | 'command_builder'
  | 'platform_tour'

export type OrientationStep = {
  id: string
  kind: string
  title: string
  prompt: string
  body?: string
  hint?: string
  accept_prefixes?: string[]
  accept_exact?: string[]
  require_processed?: boolean
  success_output?: string
  initial_state?: RepositorySnapshot
  options?: Array<{ id: string; label: string; detail: string }>
  pairs?: Array<{ scenario: string; problem: string }>
  stages?: string[]
  sample_output?: string
  parts?: string[]
  target?: string
  error_text?: string
  answer?: string
  hotspots?: string[]
}

export type ChapterOrientationLessonSummary = ApiSchemas['ChapterOrientationLessonList']

export type ChapterOrientationLessonDetail = Omit<
  ApiSchemas['ChapterOrientationLessonDetail'],
  'interaction_steps'
> & {
  interaction_steps: OrientationStep[]
}

export const LESSON_LAYOUT_BY_SLUG: Record<string, OrientationLayout> = {
  'what-is-git-and-why-it-matters': 'storyboard',
  'installing-git-and-environment': 'guide_terminal',
  'command-line-basics': 'explorer_shell',
  'git-diagram-four-areas': 'pipeline_status',
  'commits-and-history': 'anatomy',
  'reading-a-dag': 'dag_log',
  'git-command-anatomy': 'command_builder',
  'how-git-it-works': 'platform_tour',
}

export const CRITICAL_LESSON_SLUGS = new Set([
  'git-diagram-four-areas',
  'reading-a-dag',
  'git-command-anatomy',
])

export function displayLessonTitle(title: string) {
  return title.replace(/^Lesson\s+0\.\d+\s*[—–-]\s*/i, '').trim()
}

export function normalizeBuilderCommand(command: string) {
  return command
    .toLowerCase()
    .replace(/[""]/g, '"')
    .replace(/\s+/g, ' ')
    .trim()
}
