import { ArrowRight, Castle, RefreshCcw, Sparkles, XCircle } from 'lucide-react'
import { useEffect } from 'react'
import type { CSSProperties } from 'react'

import bugIconImage from '@/assets/images/battle-outcome/bug.png'
import skullIconImage from '@/assets/images/battle-outcome/skull.png'
import terminalIconImage from '@/assets/images/battle-outcome/terminal.png'
import warnIconImage from '@/assets/images/battle-outcome/warn.png'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import { GameOutcomeModal } from '@/shared/level/components/game-outcome/GameOutcomeModal'
import { Badge } from '@/shared/components/Badge'
import { Button } from '@/shared/components/Button'
import { playGameOverSound, playVictorySound } from '@/shared/audio/battleAudio'

function difficultyLabel(run: TierRun) {
  if (!run.difficulty) return 'Adventure'
  return run.difficulty.charAt(0).toUpperCase() + run.difficulty.slice(1)
}

/** Mirrors ChallengeOutcomeModal. Tiers have no sibling-level navigator - a
 * tier's only lateral move is next_difficulty (easy -> medium -> hard),
 * already surfaced via the "Next" action below. */
export function TierOutcomeModal({
  open,
  run,
  onClose,
  onBackToMap,
  onNextLevel,
  onRetry,
  onContinue,
  isStartingNextLevel = false,
  isRetrying = false,
  isContinuing = false,
  nextDifficultyLabel,
}: {
  open: boolean
  run: TierRun
  onClose: () => void
  onBackToMap: () => void
  onNextLevel?: () => void
  onRetry?: () => void
  /** Starts a fresh run on the same tier after a partial clear (progress not
   * yet at required_successful_attempts) - passes prior_run_id so
   * TierVariantSelectionService rotates to a different variant. */
  onContinue?: () => void
  isStartingNextLevel?: boolean
  isRetrying?: boolean
  isContinuing?: boolean
  nextDifficultyLabel?: string | null
}) {
  const isFailed = run.status === 'failed'
  const isReplay = run.replay
  const isNavigating = isStartingNextLevel || isRetrying || isContinuing
  const canAdvance = !isReplay && run.status === 'completed' && Boolean(run.next_difficulty)
  const isPartialClear = !isReplay && run.status === 'completed' && !canAdvance && !run.progress.cleared

  useEffect(() => {
    if (!open) return
    if (isFailed) {
      playGameOverSound()
    } else {
      playVictorySound()
    }
  }, [isFailed, open])

  const headline = isReplay
    ? isFailed
      ? 'Replay ended'
      : 'Replay complete'
    : isFailed
      ? 'Attempt limit reached'
      : canAdvance
        ? 'Level ready'
        : isPartialClear
          ? 'Scenario cleared'
          : 'Level cleared'

  const hitActionLimit = isFailed && run.counts.max_reached
  const message = isReplay
    ? isFailed
      ? "This free-play run ended before reaching the target state. It doesn't affect your saved progress. Play again whenever you like."
      : "Free play complete. This run is just a replay and doesn't change your saved progress."
    : isFailed
      ? hitActionLimit
        ? run.failure_reason ??
          'You used every counted action allowed for this attempt without reaching the target repository state. Start a fresh variant and try again.'
        : 'This attempt ended before the repository reached the target state. Start a fresh variant and try again.'
      : canAdvance
        ? 'Level cleared. The next difficulty is ready.'
        : isPartialClear
          ? `Nice work. ${run.progress.completed} of ${run.progress.total} clears done for this difficulty - continue with a new scenario to finish it.`
          : 'Level cleared.'
  const Icon = isFailed ? XCircle : Sparkles
  const stats = [
    {
      label: 'Actions',
      numerator: run.counts.counted_action_total,
      denominator: run.counts.maximum_counted_commands,
      helper: `Full stars target: ${run.counts.minimum_counted_commands}`,
      iconSrc: terminalIconImage,
    },
    {
      label: 'Diagnostics',
      numerator: run.counts.non_counted_diagnostic_total,
      helper: 'Free inspections used',
      iconSrc: bugIconImage,
    },
    {
      label: 'Attempts',
      numerator: run.counts.total_attempts,
      helper: isReplay ? 'Free-play attempt' : 'Saved attempt count',
      iconSrc: skullIconImage,
    },
  ]

  const badges = (
    <>
      <Badge
        variant={isFailed ? 'destructive' : 'default'}
        className="game-outcome-badge"
        style={{ animationDelay: '60ms' } as CSSProperties}
      >
        {isFailed ? <img className="game-outcome-badge-icon" src={warnIconImage} alt="" aria-hidden="true" /> : null}
        {difficultyLabel(run)} {isFailed ? 'failed' : 'complete'}
      </Badge>
      {isReplay ? (
        <Badge
          variant="secondary"
          className="game-outcome-badge"
          style={{ animationDelay: '140ms' } as CSSProperties}
        >
          <RefreshCcw className="size-3.5" />
          Replay
        </Badge>
      ) : null}
    </>
  )

  const actions = isReplay ? (
    <>
      {onRetry ? (
        <Button type="button" disabled={isNavigating} onClick={onRetry}>
          <RefreshCcw data-icon="inline-start" />
          {isRetrying ? 'Starting fresh run' : 'Play again'}
        </Button>
      ) : null}
      <Button type="button" variant="ghost" disabled={isNavigating} onClick={onBackToMap}>
        <Castle data-icon="inline-start" />
        Back to Map
      </Button>
    </>
  ) : isFailed ? (
    <>
      {onRetry ? (
        <Button type="button" disabled={isNavigating} onClick={onRetry}>
          <RefreshCcw data-icon="inline-start" />
          {isRetrying ? 'Starting fresh variant' : 'Start fresh variant'}
        </Button>
      ) : null}
      <Button type="button" variant="ghost" disabled={isNavigating} onClick={onBackToMap}>
        <Castle data-icon="inline-start" />
        Back to Map
      </Button>
    </>
  ) : canAdvance ? (
    <>
      {onNextLevel && nextDifficultyLabel ? (
        <Button type="button" disabled={isNavigating} onClick={onNextLevel}>
          <ArrowRight data-icon="inline-start" />
          {isStartingNextLevel ? 'Opening next level' : `Next: ${nextDifficultyLabel}`}
        </Button>
      ) : null}
      <Button type="button" variant="secondary" disabled={isNavigating} onClick={onClose}>
        Stay in workspace
      </Button>
    </>
  ) : isPartialClear ? (
    <>
      {onContinue ? (
        <Button type="button" disabled={isNavigating} onClick={onContinue}>
          <ArrowRight data-icon="inline-start" />
          {isContinuing ? 'Starting next scenario' : 'Continue to next scenario'}
        </Button>
      ) : null}
      <Button type="button" variant="ghost" disabled={isNavigating} onClick={onBackToMap}>
        <Castle data-icon="inline-start" />
        Back to Map
      </Button>
    </>
  ) : run.status === 'completed' ? (
    <Button type="button" variant="ghost" disabled={isNavigating} onClick={onBackToMap}>
      <Castle data-icon="inline-start" />
      Back to Map
    </Button>
  ) : null

  return (
    <GameOutcomeModal
      open={open}
      onClose={onClose}
      title={isFailed ? 'Level failed' : 'Level complete'}
      tone={isFailed ? 'failure' : 'success'}
      icon={Icon}
      resultLabel={isFailed ? 'Game Over' : 'You Won'}
      stars={run.stars}
      badges={badges}
      headline={headline}
      message={message}
      stats={stats}
      actions={actions}
    />
  )
}
