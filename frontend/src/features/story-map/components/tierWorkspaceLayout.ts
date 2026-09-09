import { storyPath, storyPathWithQuery } from '@/shared/navigation/routes'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'

export const DEFAULT_TERMINAL_RATIO = 0.28
export const DEFAULT_TARGET_DIAGRAM_RATIO = 0.5
export const DEFAULT_TERMINAL_PANE_RATIO = 0.60
const RESIZE_HANDLE_WIDTH = 6
export const TERMINAL_RATIO_KEY = 'tier-workspace:terminal-ratio'
export const TARGET_DIAGRAM_RATIO_KEY = 'tier-workspace:target-diagram-ratio'
export const TERMINAL_PANE_RATIO_KEY = 'tier-workspace:terminal-pane-ratio'
export const DAG_ZOOM_KEY = 'tier-workspace:dag-zoom-vertical'

const MIN_TERMINAL_PANE_WIDTH = 544
const MIN_FEEDBACK_PANE_WIDTH = 288
const MAX_FEEDBACK_PANE_WIDTH = 480

export function ratioSanitizer(min: number, max: number, fallback: number) {
  return (value: number) =>
    typeof value === 'number' && Number.isFinite(value) ? clamp(value, min, max) : fallback
}

export function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

export function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

export function mapUrlForRun(run: Pick<TierRun, 'chapter' | 'story'>) {
  const storySlug = run.story?.slug
  return run.chapter
    ? storyPathWithQuery(storySlug, `chapter=${run.chapter.id}`)
    : storyPath(storySlug)
}

export function constrainedTerminalPaneRatio(clientX: number, bounds: DOMRect) {
  const usableWidth = Math.max(bounds.width - RESIZE_HANDLE_WIDTH, 1)
  const rawRatio = (clientX - bounds.left) / bounds.width
  const minRatio = Math.max(
    MIN_TERMINAL_PANE_WIDTH / usableWidth,
    1 - MAX_FEEDBACK_PANE_WIDTH / usableWidth,
  )
  const maxRatio = 1 - MIN_FEEDBACK_PANE_WIDTH / usableWidth

  if (minRatio > maxRatio) {
    return clamp(rawRatio, 0.58, 0.86)
  }

  return clamp(rawRatio, minRatio, maxRatio)
}
