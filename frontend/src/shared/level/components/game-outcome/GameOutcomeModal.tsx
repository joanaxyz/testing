import type { ComponentType, ReactNode } from 'react'
import { X } from 'lucide-react'

import titlesImage from '@/assets/images/battle-outcome/titles.webp'
import { isMotionReduced } from '@/shared/battle/hooks/battleMotion'
import { Button } from '@/shared/components/Button'
import { Modal } from '@/shared/components/Modal'
import { cn } from '@/shared/utils/cn'
import { useLazyImage } from '@/shared/utils/useLazyImage'

import { GameOutcomeConfetti } from './GameOutcomeConfetti'
import { GameOutcomeStarBurst } from './GameOutcomeStarBurst'
import { GameOutcomeStatTile } from './GameOutcomeStatTile'

// Entrance choreography: the crest (stars/icon) lands first, one star at a
// time, then the "You Won" wordmark, then the supporting copy, then the
// stats - guiding the eye top to bottom instead of everything popping in at
// once. All of this collapses to instant when isMotionReduced().
const STAR_POP_START_MS = 120
const STAR_POP_STEP_MS = 170
const CREST_POP_DURATION_MS = 420
const POST_CREST_GAP_MS = 200
const SUBLINE_GAP_MS = 150
const STAT_GRID_GAP_MS = 300

// A single outcome shows exactly one star-arc image (the loss art, or one of
// three win tiers), so each is imported lazily instead of bundling all four
// upfront. `titlesImage` above is shown on every outcome, so it stays a
// normal static import.
const STAR_ART_LOADERS: Record<string, () => Promise<{ default: string }>> = {
  lose: () => import('@/assets/images/battle-outcome/lose-0.webp'),
  'win-1': () => import('@/assets/images/battle-outcome/win-1.webp'),
  'win-2': () => import('@/assets/images/battle-outcome/win-2.webp'),
  'win-3': () => import('@/assets/images/battle-outcome/win-3.webp'),
}

export type GameOutcomeStat = {
  label: string
  numerator: number
  denominator?: number
  suffix?: string
  helper: string
  icon?: ComponentType<{ className?: string }>
  /** Neon icon art (battle-outcome assets); wins over `icon` when set. */
  iconSrc?: string
}

/**
 * Shared game result overlay for challenge and adventure run endings. Feature
 * wrappers own outcome state and copy; this component owns the visual chrome.
 */
export function GameOutcomeModal({
  open,
  onClose,
  title,
  tone = 'success',
  icon: Icon,
  resultLabel,
  stars,
  badges,
  headline,
  message,
  note,
  stats,
  children,
  actions,
  className,
}: {
  open: boolean
  onClose: () => void
  title: string
  tone?: 'success' | 'failure'
  icon: ComponentType<{ className?: string }>
  /** Large result wordmark, e.g. "You Won" or "Game Over". */
  resultLabel?: string
  /** Stars earned, shown as the hero crest when provided. */
  stars?: number
  badges?: ReactNode
  headline: string
  message: ReactNode
  /** Optional emphasised aside under the message. */
  note?: ReactNode
  stats?: GameOutcomeStat[]
  /** Surface-specific section rendered between the stats and the actions. */
  children?: ReactNode
  actions?: ReactNode
  className?: string
}) {
  const isFailed = tone === 'failure'
  const earnedStars = Number.isFinite(stars) ? Math.max(0, Math.min(3, Math.floor(stars ?? 0))) : null
  const displayLabel = resultLabel ?? (isFailed ? 'Game Over' : 'You Won')
  // Failure always shows the shattered arc; wins need at least one earned star
  // (the arc art has no zero-star variant, so starless wins keep the icon crest).
  const starArtKey = isFailed ? 'lose' : earnedStars && earnedStars > 0 ? `win-${earnedStars}` : null
  const starArt = useLazyImage(starArtKey, STAR_ART_LOADERS)
  const statAccent = isFailed ? 'hsl(var(--destructive))' : 'hsl(var(--primary))'
  const reduceMotion = isMotionReduced()

  // Stars land one at a time (with a burst under each), then everything
  // below waits its turn - each stage's delay is derived from when the one
  // above it finishes, so the sequence stays coherent whether there are 1,
  // 2 or 3 stars, or no star sequence at all (icon crest / loss art).
  const earnedStarsCount = earnedStars ?? 0
  const hasStarSequence = !isFailed && !!starArt && earnedStarsCount > 0
  const crestSequenceEndMs = hasStarSequence
    ? STAR_POP_START_MS + (earnedStarsCount - 1) * STAR_POP_STEP_MS + CREST_POP_DURATION_MS
    : CREST_POP_DURATION_MS
  const titleDelayMs = reduceMotion ? 0 : crestSequenceEndMs + POST_CREST_GAP_MS
  const sublineDelayMs = reduceMotion ? 0 : titleDelayMs + SUBLINE_GAP_MS
  const statGridBaseDelayMs = reduceMotion ? 0 : titleDelayMs + STAT_GRID_GAP_MS

  return (
    <Modal
      open={open}
      title={title}
      className={cn('game-outcome-shell w-full max-w-5xl overflow-hidden', className)}
      overlayClassName="game-outcome-backdrop"
      contentClassName="p-0"
      hideHeader
      onClose={onClose}
    >
      <div className={cn('game-outcome relative overflow-hidden', isFailed ? 'is-failure' : 'is-success')}>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="game-outcome-close"
          onClick={onClose}
          aria-label="Close modal"
        >
          <X className="size-4" />
        </Button>
        {!isFailed ? <GameOutcomeConfetti /> : null}

        <div className="game-outcome-hero relative text-center">
          <div className="game-outcome-crest relative">
            {starArt ? (
              <img
                className={cn('game-outcome-star-art game-outcome-crest-enter', !isFailed && 'game-outcome-sparkle-glow')}
                src={starArt}
                alt={isFailed ? 'No stars earned' : `${earnedStars} of 3 stars earned`}
              />
            ) : (
              <div
                className={cn('game-outcome-icon-crest game-outcome-crest-enter', !isFailed && 'game-outcome-sparkle-glow')}
                aria-hidden="true"
              >
                <Icon className="game-outcome-result-icon" />
              </div>
            )}
            {hasStarSequence && !reduceMotion ? (
              <GameOutcomeStarBurst earnedStars={earnedStarsCount} startDelayMs={STAR_POP_START_MS} stepMs={STAR_POP_STEP_MS} />
            ) : null}
          </div>

          <div
            className={cn(
              'game-outcome-title-art game-outcome-headline',
              isFailed && 'is-lost',
              starArt && 'has-star-arc',
            )}
            role="img"
            aria-label={displayLabel}
            style={{ backgroundImage: `url(${titlesImage})`, animationDelay: `${titleDelayMs}ms` }}
          />
          <h3
            className="game-outcome-subline game-outcome-fade-up mx-auto mt-2 max-w-xl text-balance text-base font-extrabold sm:text-lg"
            style={{ animationDelay: `${sublineDelayMs}ms` }}
          >
            {headline}
          </h3>

          {badges ? <div className="mt-2 flex flex-wrap justify-center gap-2">{badges}</div> : null}

          {/* Quiet subtext under the badges - real information (what unlocked,
              what to do next), but it shouldn't compete with the "You Won"
              headline for attention, so it reads small and muted rather than
              as a second sentence-sized headline. */}
          <p
            className="game-outcome-message game-outcome-fade-up mx-auto mt-1 max-w-xl text-xs leading-5 text-muted-foreground"
            style={{ animationDelay: `${sublineDelayMs + 60}ms` }}
          >
            {message}
          </p>
          {note ? <p className="mx-auto mt-1 max-w-xl text-xs font-medium leading-5 text-warning">{note}</p> : null}

          {stats && stats.length ? (
            <div className="game-outcome-stat-grid mt-3 grid grid-cols-2 gap-2.5 text-left sm:grid-cols-3">
              {stats.map((stat, index) => (
                <GameOutcomeStatTile
                  key={stat.label}
                  {...stat}
                  accentColor={statAccent}
                  animationDelay={reduceMotion ? 0 : statGridBaseDelayMs + index * 60}
                />
              ))}
            </div>
          ) : null}

          {children}

          {actions ? <div className="game-outcome-actions mt-3 flex flex-wrap justify-center gap-3">{actions}</div> : null}
        </div>
      </div>
    </Modal>
  )
}
