import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, Lock, Play, Swords } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { AdventureLevelSummary, AdventureLevelTierAccess, ChallengeSummary } from '@/features/story-map/types'
import {
  actionForChallengeLevel,
  actionLabel,
  allChallengeTrials,
  challengeLevelAccent,
  difficultyLabel,
} from '@/features/story-map/utils/challengeUi'
import { pathDataFor, pathGeometry } from '@/features/story-map/utils/pathGeometry'
import { useStoryArtifactNavigation } from '@/features/story-map/hooks/useStoryArtifactNavigation'
import type { LearningChapter } from '@/features/story-map/types'
import { tierRunsApi } from '@/features/story-map/api/tierRunsApi'
import { syncTierRunInCache } from '@/features/story-map/utils/tierRunCache'
import { StarRating, type StarFillState } from '@/shared/level/components/StarRating'
import { useFocusTrap } from '@/shared/utils/useFocusTrap'

import easyIconImage from '@/assets/images/easy_icon.png'
import hardIconImage from '@/assets/images/hard_icon.png'
import mediumIconImage from '@/assets/images/medium_icon.png'
import { adventureLevelCleared, nextPlayableLevelId } from '@/features/story-map/utils/storyMapChapter'

const DIFFICULTY_ORDER = ['easy', 'medium', 'hard'] as const
const DIFFICULTY_ICONS: Record<(typeof DIFFICULTY_ORDER)[number], string> = {
  easy: easyIconImage,
  medium: mediumIconImage,
  hard: hardIconImage,
}
const DIFFICULTY_TIER_LABELS: Record<(typeof DIFFICULTY_ORDER)[number], string> = {
  easy: 'Easy',
  medium: 'Medium',
  hard: 'Hard',
}

const PILL_CLOSE_MS = 180

// Node-level star display only: one star per difficulty tier (easy/medium/
// hard, in that order), full once that tier is completed, half while a wave
// is in progress on it, empty otherwise. Distinct from the numeric `stars`
// grade used by the tier-popup and challenge-trial-card StarRating call
// sites, which this deliberately leaves untouched.
function tierStarFillStates(tiers: AdventureLevelTierAccess[]): StarFillState[] {
  return DIFFICULTY_ORDER.map((difficulty) => {
    const tier = tiers.find((candidate) => candidate.difficulty === difficulty)
    if (!tier) return 'empty'
    if (tier.completion) return 'full'
    if (tier.wave_progress.completed > 0 && tier.wave_progress.completed < tier.wave_progress.total) {
      return 'half'
    }
    return 'empty'
  })
}

export function StoryAdventurePath({
  chapter,
  levels,
  challenges,
  challengesLocked,
  loading,
  defaultTrialsOpen = false,
}: {
  chapter: LearningChapter
  levels: AdventureLevelSummary[]
  challenges: ChallengeSummary[]
  challengesLocked: boolean
  loading: boolean
  defaultTrialsOpen?: boolean
}) {
  const { openAdventureLevel, openChallengeArtifact } = useStoryArtifactNavigation()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const startTierRunMutation = useMutation({
    mutationFn: ({ tierId, replay }: { tierId: number; replay?: boolean }) =>
      tierRunsApi.startRun(tierId, replay ? { replay: true } : undefined),
    onSuccess: (run) => {
      syncTierRunInCache(queryClient, run)
      navigate(`/adventure-tier-runs/${run.id}`)
    },
  })
  const currentLevelId = nextPlayableLevelId(levels, chapter.locked)
  const placeholderCount = Math.max(3, chapter.adventure_level_count || 6)
  const nodes: Array<AdventureLevelSummary | undefined> = levels.length
    ? levels
    : Array.from({ length: placeholderCount })
  const trials = allChallengeTrials(challenges)
  const [trialsOpen, setTrialsOpen] = useState(defaultTrialsOpen)
  const trialsPanelRef = useRef<HTMLElement | null>(null)
  const [selectedLevelId, setSelectedLevelId] = useState<number | null>(null)
  const [closingLevelId, setClosingLevelId] = useState<number | null>(null)
  const closeTimerRef = useRef<number | null>(null)

  const pathRef = useRef<HTMLDivElement | null>(null)
  const [pathWidth, setPathWidth] = useState(640)
  useEffect(() => {
    const el = pathRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width ?? 0
      if (width > 0) setPathWidth(Math.max(320, Math.min(720, Math.round(width))))
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  function queueClosingPill(levelId: number) {
    if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current)
    setClosingLevelId(levelId)
    closeTimerRef.current = window.setTimeout(() => {
      setClosingLevelId((current) => (current === levelId ? null : current))
      closeTimerRef.current = null
    }, PILL_CLOSE_MS)
  }

  function toggleLevelPill(levelId: number) {
    if (selectedLevelId === levelId) {
      queueClosingPill(levelId)
      setSelectedLevelId(null)
      return
    }
    if (selectedLevelId !== null) queueClosingPill(selectedLevelId)
    setClosingLevelId((closing) => (closing === levelId ? null : closing))
    setSelectedLevelId(levelId)
  }

  useEffect(() => {
    setTrialsOpen(defaultTrialsOpen)
    setSelectedLevelId(null)
    setClosingLevelId(null)
  }, [chapter.id, defaultTrialsOpen])

  useEffect(() => {
    if (selectedLevelId && !levels.some((level) => level.id === selectedLevelId && !level.locked)) {
      setSelectedLevelId(null)
    }
  }, [levels, selectedLevelId])

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current)
    }
  }, [])

  useEffect(() => {
    if (!trialsOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setTrialsOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [trialsOpen])

  useEffect(() => {
    if (!trialsOpen) return
    const frame = window.requestAnimationFrame(() => {
      trialsPanelRef.current?.scrollIntoView?.({ block: 'nearest' })
    })
    return () => window.cancelAnimationFrame(frame)
  }, [trialsOpen])

  // Traps focus inside the trials panel while open and restores it to
  // whatever opened it (the Challenge Gate node button) when it closes —
  // otherwise closing via Escape drops focus into the void, since the
  // focused trial card unmounts along with the rest of the panel.
  useFocusTrap(trialsPanelRef, trialsOpen)

  // One extra point: the chapter's challenge trials live on the same path,
  // as its final node.
  const { points, height } = useMemo(
    () => pathGeometry(nodes.length + 1, pathWidth),
    [nodes.length, pathWidth],
  )
  const routePathData = useMemo(() => pathDataFor(points), [points])
  const trialPoint = points[points.length - 1]

  const selectedTierNodeIndex = useMemo(
    () => nodes.findIndex((node) => node && node.id === selectedLevelId && node.tiers.length > 0),
    [nodes, selectedLevelId],
  )
  const selectedTierLevel =
    selectedTierNodeIndex >= 0 ? (nodes[selectedTierNodeIndex] as AdventureLevelSummary) : null
  const selectedTierPoint = selectedTierNodeIndex >= 0 ? points[selectedTierNodeIndex] : null
  const levelTierPanelRef = useRef<HTMLElement | null>(null)
  const [levelTierPanelSize, setLevelTierPanelSize] = useState({ width: 0, height: 0 })
  useFocusTrap(levelTierPanelRef, Boolean(selectedTierLevel))

  // Measure the panel's rendered size so it can be flipped to whichever side
  // has room, without a layout-thrash loop (size only changes when the
  // panel's content changes, not on every scroll/resize).
  useEffect(() => {
    const el = levelTierPanelRef.current
    if (!el || !selectedTierLevel) {
      setLevelTierPanelSize({ width: 0, height: 0 })
      return
    }
    const rect = el.getBoundingClientRect()
    setLevelTierPanelSize({ width: rect.width, height: rect.height })
  }, [selectedTierLevel])

  const trialsCleared = trials.length > 0 && trials.every((trial) => trial.completion)
  const clearedTrialCount = trials.filter((trial) => trial.completion).length
  const trialState = loading
    ? 'loading'
    : challengesLocked || !trials.length
    ? 'locked'
    : trialsCleared
    ? 'cleared'
    : 'ready'
  const trialDisabled = trialState === 'locked' || trialState === 'loading'

  // Anchor the tier panel beside its node - a compact popup, not a banner.
  // Prefers whichever side (right or left) has more room in the canvas, and
  // clamps vertically so it never renders above/below the canvas edges.
  const TIER_PANEL_WIDTH = 260
  const TIER_PANEL_GAP = 14
  const NODE_HALF = 28
  const levelTierPanelStyle: React.CSSProperties | undefined = selectedTierPoint
    ? (() => {
        const spaceRight = pathWidth - (selectedTierPoint.x + NODE_HALF)
        const spaceLeft = selectedTierPoint.x - NODE_HALF
        const openRight = spaceRight >= TIER_PANEL_WIDTH + TIER_PANEL_GAP || spaceRight >= spaceLeft
        const left = openRight
          ? selectedTierPoint.x + NODE_HALF + TIER_PANEL_GAP
          : selectedTierPoint.x - NODE_HALF - TIER_PANEL_GAP - TIER_PANEL_WIDTH
        const clampedLeft = Math.min(Math.max(left, 0), Math.max(pathWidth - TIER_PANEL_WIDTH, 0))
        const idealTop = selectedTierPoint.y - levelTierPanelSize.height / 2
        const top = Math.min(
          Math.max(idealTop, 0),
          Math.max(height - levelTierPanelSize.height, 0),
        )
        return { left: clampedLeft, top, width: TIER_PANEL_WIDTH }
      })()
    : undefined

  return (
    <div className="story-adventure-path" ref={pathRef}>
      <div className="story-path-canvas" style={{ width: pathWidth, height }}>
        <svg
          className="story-route-line"
          viewBox={`0 0 ${pathWidth} ${height}`}
          width={pathWidth}
          height={height}
          aria-hidden="true"
          focusable="false"
        >
          <path d={routePathData} />
        </svg>

        {nodes.map((node, index) => {
          const level = node
          const pos = points[index]
          const state = level
            ? level.locked || chapter.locked
              ? 'locked'
              : adventureLevelCleared(level)
              ? 'cleared'
              : level.id === currentLevelId
              ? 'current'
              : 'ready'
            : loading
            ? 'loading'
            : 'locked'
          const hasTiers = Boolean(level && level.tiers.length > 0)
          const starFillStates = level && hasTiers ? tierStarFillStates(level.tiers) : undefined
          const stars = level?.completion?.stars ?? 0
          const disabled = !level || state === 'locked' || state === 'loading'
          const selected = Boolean(level && selectedLevelId === level.id)
          const closing = Boolean(level && closingLevelId === level.id && !selected)
          const showPlayPill = Boolean(level && !hasTiers && (selected || closing))

          return (
            <div
              className="story-path-node"
              data-state={state}
              data-selected={selected || undefined}
              key={level?.id ?? `placeholder-${index}`}
              style={{ '--node-x': `${pos.x}px`, '--node-y': `${pos.y}px` } as React.CSSProperties}
            >
              <button
                type="button"
                className="story-path-node-button"
                data-onboarding={level?.id === currentLevelId && !disabled ? 'next-level' : undefined}
                disabled={disabled}
                aria-label={
                  level
                    ? `Level ${index + 1}: ${level.title}. ${selected ? 'Play action open' : 'Open play action'}.`
                    : `Locked level ${index + 1}`
                }
                aria-expanded={level ? selected : undefined}
                onClick={() => {
                  if (!level) return
                  toggleLevelPill(level.id)
                }}
              >
                <span className="story-path-node-ring">
                  {state === 'locked' ? <Lock className="size-5" aria-hidden="true" /> : <span>{index + 1}</span>}
                </span>
                {state === 'cleared' ? (
                  <span className="story-path-node-badge" aria-hidden="true">
                    <Check className="size-3.5" strokeWidth={3} />
                  </span>
                ) : null}
              </button>

              {showPlayPill ? (
                <button
                  type="button"
                  className="story-path-node-play"
                  data-pill-state={closing ? 'closing' : 'open'}
                  aria-label={`Play ${level!.title}`}
                  onClick={() => openAdventureLevel(level!)}
                >
                  <Play className="size-4" fill="currentColor" aria-hidden="true" />
                  <span className="sr-only">Play</span>
                </button>
              ) : null}

              {state === 'locked' || state === 'loading' ? null : (
                <StarRating
                  stars={starFillStates ? undefined : stars}
                  fillStates={starFillStates}
                  size="sm"
                  className="story-path-stars"
                  label={level?.title ?? 'Level'}
                />
              )}
            </div>
          )
        })}

        <button
          type="button"
          className="story-path-node story-path-node--trial"
          data-onboarding={trials.length > 0 ? 'challenges' : undefined}
          data-state={trialState}
          data-open={trialsOpen || undefined}
          style={{ '--node-x': `${trialPoint.x}px`, '--node-y': `${trialPoint.y}px` } as React.CSSProperties}
          disabled={trialDisabled}
          title={
            trialState === 'locked' && !loading
              ? chapter.locked
                ? chapter.lock_reason
                : 'Clear the adventure levels to unlock the trials.'
              : undefined
          }
          aria-label={trialState === 'locked' ? 'Challenge trials (locked)' : 'Challenge trials'}
          aria-expanded={trialsOpen}
          aria-controls="story-challenge-panel"
          onClick={() => setTrialsOpen((open) => !open)}
        >
          <span className="story-path-node-ring">
            {trialState === 'locked' ? (
              <Lock className="size-5" aria-hidden="true" />
            ) : (
              <Swords className="size-6" aria-hidden="true" />
            )}
          </span>
          <span className="story-challenge-node-label">Challenge Gate</span>
          {trialState === 'cleared' ? (
            <span className="story-path-node-badge" aria-hidden="true">
              <Check className="size-3.5" strokeWidth={3} />
            </span>
          ) : null}
        </button>

        {selectedTierLevel && levelTierPanelStyle ? (
          <section
            id="story-level-tier-panel"
            ref={levelTierPanelRef}
            className="story-level-tier-panel"
            style={levelTierPanelStyle}
            aria-labelledby="story-level-tier-panel-title"
          >
            <header className="story-level-tier-panel-header">
              <h2 id="story-level-tier-panel-title">{selectedTierLevel.title}</h2>
              <p>{selectedTierLevel.description}</p>
            </header>

            <div className="story-level-tier-panel-list">
              {DIFFICULTY_ORDER.map((difficulty) => {
                const tier: AdventureLevelTierAccess | undefined = selectedTierLevel.tiers.find(
                  (item) => item.difficulty === difficulty,
                )
                const isLocked = !tier || tier.locked
                const isCleared = Boolean(tier?.completion)
                const stars = tier?.completion?.stars ?? 0
                const progress = tier?.wave_progress ?? { completed: 0, total: 0 }
                const isReplay = isCleared
                const status = isLocked
                  ? 'locked'
                  : isCleared
                  ? 'cleared'
                  : progress.completed > 0
                  ? 'in_progress'
                  : 'not_started'
                const actionLabel =
                  status === 'cleared' ? 'Review' : status === 'in_progress' ? 'Continue' : 'Start'
                const isStartingThisTier =
                  startTierRunMutation.isPending && startTierRunMutation.variables?.tierId === tier?.id
                const isDisabled = isLocked || !tier || startTierRunMutation.isPending

                return (
                  <button
                    type="button"
                    className="story-level-tier-card"
                    data-status={status}
                    key={`${selectedTierLevel.id}-${difficulty}`}
                    disabled={isDisabled}
                    aria-label={`${selectedTierLevel.title}: ${difficulty} tier. ${actionLabel}.`}
                    title={isLocked ? 'Clear the previous difficulty to unlock this tier.' : undefined}
                    onClick={() => {
                      if (!tier || isLocked) return
                      startTierRunMutation.mutate({ tierId: tier.id, replay: isReplay })
                    }}
                  >
                    <span className="story-level-tier-card-medallion">
                      <img src={DIFFICULTY_ICONS[difficulty]} alt="" />
                      {isLocked ? <Lock className="story-trial-lock" aria-hidden="true" /> : null}
                    </span>
                    <span className="story-level-tier-card-copy">
                      <strong>{DIFFICULTY_TIER_LABELS[difficulty]}</strong>
                      <StarRating stars={stars} size="sm" label={`${difficulty} stars`} />
                    </span>
                    {isLocked ? (
                      <span className="story-level-tier-card-progress">
                        {progress.completed}/{progress.total}
                      </span>
                    ) : (
                      <span className="story-level-tier-card-cta">
                        <span className="story-level-tier-card-action">
                          {isStartingThisTier ? 'Starting…' : actionLabel}
                        </span>
                        <span className="story-level-tier-card-progress">
                          {progress.completed}/{progress.total}
                        </span>
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          </section>
        ) : null}
      </div>

      {trialsOpen ? (
        <section
          id="story-challenge-panel"
          ref={trialsPanelRef}
          className="story-trials-panel"
          aria-labelledby="story-challenge-panel-title"
        >
          <header className="story-trials-panel-header">
            <span className="story-trials-panel-mark" aria-hidden="true">
              <Swords />
            </span>
            <div>
              <h2 id="story-challenge-panel-title">Challenge Gate</h2>
              <p>Clear each trial to master the chapter.</p>
            </div>
            <span className="story-trials-panel-progress">
              {clearedTrialCount} / {trials.length} cleared
            </span>
          </header>

          <div className="story-trials-panel-content">
            {/* One section per challenge level: a chapter can carry several
                challenge scenarios, and every trial of each must stay reachable. */}
            {challenges.map((challenge) => (
              <section className="story-trials-group" key={challenge.id} aria-labelledby={`challenge-${challenge.id}-title`}>
                <h3 id={`challenge-${challenge.id}-title`} className="story-trials-group-title">
                  {challenge.title}
                </h3>
                <div className="story-trials-grid">
                  {DIFFICULTY_ORDER.map((difficulty) => {
                    const trial =
                      challenge.trials.find((item) => String(item.difficulty) === difficulty) ?? null
                    const action = trial ? actionForChallengeLevel(trial) : null
                    const isLocked = challengesLocked || !trial || !action || trial.status === 'locked'
                    const status = loading ? 'loading' : isLocked ? 'locked' : trial.status
                    const stars = trial?.completion?.stars ?? 0
                    const accent = challengeLevelAccent(trial)

                    return (
                      <button
                        type="button"
                        className="story-trial-card"
                        data-status={status}
                        key={`${challenge.id}-${difficulty}`}
                        disabled={isLocked || loading}
                        style={{ '--trial-rgb': accent } as React.CSSProperties}
                        aria-label={`${challenge.title}: ${difficulty} challenge trial`}
                        onClick={() => {
                          if (!trial || !action) return
                          openChallengeArtifact(trial, action)
                        }}
                      >
                        <span className="story-trial-medallion">
                          <img src={DIFFICULTY_ICONS[difficulty]} alt="" />
                          {status === 'locked' || status === 'loading' ? (
                            <Lock className="story-trial-lock" aria-hidden="true" />
                          ) : null}
                        </span>
                        <span className="story-trial-copy">
                          <strong>{trial ? difficultyLabel(trial) : difficulty}</strong>
                          <StarRating stars={stars} size="sm" label={`${difficulty} stars`} />
                          <span>{trial ? actionLabel(action, trial.status) : 'Locked'}</span>
                        </span>
                      </button>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
