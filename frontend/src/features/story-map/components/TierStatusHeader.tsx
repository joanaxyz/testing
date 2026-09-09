import { RefreshCcw, X } from 'lucide-react'

import gitLogoImage from '@/assets/images/GIT_logo.webp'
import { AudioControls } from '@/shared/audio/AudioControls'
import { WorkspaceHeaderAccount } from '@/shared/level/components/WorkspaceHeaderAccount'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'

/** Mirrors ChallengeStatusHeader for the adventure-tier run lifecycle. */
export function TierStatusHeader({
  run,
  isExiting = false,
  isRetrying = false,
  onExit,
  onRetry,
  onStartOver,
  onReplay,
}: {
  run: TierRun
  isExiting?: boolean
  isRetrying?: boolean
  onExit?: () => void
  onRetry?: () => void
  onStartOver?: () => void
  onReplay?: () => void
}) {
  const exitLabel = run.status === 'started' ? 'Exit' : 'Back'
  const canRetry = !run.replay && run.status === 'failed' && !!onRetry
  const canStartOver = !run.replay && run.status === 'started' && !!onStartOver
  const canReplay = run.replay && !!onReplay
  const replayLabel = run.status === 'started' ? 'Start over' : 'Play again'
  const replayIsStartOver = replayLabel === 'Start over'
  const replayActionLabel = isRetrying ? 'Starting' : replayLabel
  const startOverLabel = isRetrying ? 'Starting over' : 'Start over'

  return (
    <header className="gameplay-workspace-header" aria-label="Adventure command bar">
      <button
        type="button"
        className="gameplay-header-close"
        disabled={isExiting}
        title={exitLabel}
        aria-label={isExiting ? 'Exiting' : exitLabel}
        onClick={onExit}
      >
        <X aria-hidden="true" />
      </button>

      <a className="gameplay-header-brand" href="/home" aria-label="GIT it! home">
        <img src={gitLogoImage} alt="" />
        <span>GIT it!</span>
      </a>

      <div className="gameplay-header-mission" aria-label="Current adventure">
        <span>Adventure · {run.difficulty ?? 'Level'}</span>
        <strong>{run.tier.adventure_level_title}</strong>
      </div>

      <span className="gameplay-header-spacer" aria-hidden="true" />

      <AudioControls
        className="gameplay-header-audio-controls"
        buttonClassName="gameplay-header-button gameplay-header-icon-button gameplay-header-audio"
      />

      {canRetry ? (
        <button type="button" className="gameplay-header-button" disabled={isRetrying} onClick={onRetry}>
          <RefreshCcw aria-hidden="true" />
          {isRetrying ? 'Starting retry' : 'Retry'}
        </button>
      ) : null}
      {canStartOver ? (
        <button
          type="button"
          className="gameplay-header-button gameplay-header-icon-button"
          disabled={isRetrying}
          title={startOverLabel}
          aria-label={startOverLabel}
          onClick={onStartOver}
        >
          <RefreshCcw aria-hidden="true" />
        </button>
      ) : null}
      {canReplay ? (
        <button
          type="button"
          className={`gameplay-header-button${replayIsStartOver ? ' gameplay-header-icon-button' : ''}`}
          disabled={isRetrying}
          title={replayActionLabel}
          aria-label={replayActionLabel}
          onClick={onReplay}
        >
          <RefreshCcw aria-hidden="true" />
          {replayIsStartOver ? null : replayActionLabel}
        </button>
      ) : null}

      <WorkspaceHeaderAccount />
    </header>
  )
}
