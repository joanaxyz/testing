import { ArrowRight, BookOpen, Castle, CheckCircle2, ChevronDown, DoorOpen, RefreshCcw, Sparkles, Trophy, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'

import forkIconImage from '@/assets/images/battle-outcome/fork.png'
import swordsIconImage from '@/assets/images/battle-outcome/swords.png'
import trophyIconImage from '@/assets/images/battle-outcome/trophy.png'
import type { AdventureRun } from '@/features/adventures/types'
import { GameOutcomeModal } from '@/shared/level/components/game-outcome/GameOutcomeModal'
import { Badge } from '@/shared/components/Badge'
import { Button } from '@/shared/components/Button'
import { playGameOverSound, playVictorySound } from '@/shared/audio/battleAudio'
import { cn } from '@/shared/utils/cn'

// The single outcome surface shown when an adventure run ends. It reuses the
// shared GameOutcomeModal so adventures and challenges resolve the same way;
// the level navigator is challenge-only, so it is simply omitted here, while the
// per-command mastery breakdown is the adventure-specific extra section.
export function AdventureOutcomeModal({
  open,
  run,
  onRestart,
  onNextLevel,
  onBackToMap,
  onClose,
  isOpeningNextLevel = false,
  isRestarting = false,
}: {
  open: boolean
  run: AdventureRun
  onRestart: () => void
  onNextLevel?: () => void
  onBackToMap?: () => void
  onClose: () => void
  isOpeningNextLevel?: boolean
  isRestarting?: boolean
}) {
  const { passed, commands } = run.mastery
  const isReplay = run.replay
  const isDefeated = run.status === 'failed'
  const isFailed = isDefeated || (!isReplay && !passed)
  const hasPerfectScore = run.stars >= 3
  const wonBelowPerfect = !isFailed && run.status === 'completed' && !hasPerfectScore
  const runTitle = run.selected_level?.title ?? run.story?.title ?? 'Story'
  // The per-command breakdown is a detail view - the stat grid above already
  // surfaces the "commands mastered" total, so collapse it by default and
  // let players expand when they want the full list.
  const [masteryExpanded, setMasteryExpanded] = useState(false)

  useEffect(() => {
    if (!open) return
    if (isFailed) {
      playGameOverSound()
    } else {
      playVictorySound()
    }
  }, [isFailed, open])

  const headline = isReplay
    ? isDefeated
      ? 'Replay failed'
      : 'Replay complete'
    : isFailed
      ? 'Adventure failed'
      : 'Adventure cleared'
  const message = isReplay
    ? isDefeated
      ? 'Your health was depleted before you cleared the encounter. Start a fresh run whenever you want another attempt.'
      : wonBelowPerfect
      ? 'Replay complete. Try again to improve the saved star score, or keep moving through the story.'
      : 'Replay complete. Mastery and unlock progress stay unchanged.'
    : isDefeated
      ? 'Your health was depleted before you cleared the encounter. Start a fresh run and try again.'
      : wonBelowPerfect
        ? "You cleared the adventure. Retry this level for a perfect score, or continue when you're ready."
      : passed
        ? "You cleared the adventure and unlocked this chapter's Challenge. Replay any time to sharpen your commands."
        : 'The repository never reached the required state. Start a fresh run and try again.'

  const playAgainLabel = wonBelowPerfect ? 'Retry' : isReplay || passed ? 'Play again' : 'Try again'
  const handleNextLevel = !isFailed && run.next_level && onNextLevel ? onNextLevel : null
  const isNavigating = isOpeningNextLevel || isRestarting
  const stats = [
    {
      label: 'Commands',
      numerator: run.mastery.commands_mastered,
      denominator: run.mastery.total_commands,
      helper: 'Commands mastered',
      iconSrc: trophyIconImage,
    },
    {
      label: 'Progress',
      numerator: run.progress.completed,
      denominator: run.progress.total,
      helper: 'Levels cleared',
      iconSrc: forkIconImage,
    },
    {
      label: 'Waves',
      numerator: run.current_wave,
      denominator: run.total_waves,
      helper: 'Encounters reached',
      iconSrc: swordsIconImage,
    },
  ]

  const badges = (
    <>
      {isReplay ? (
        <Badge variant="secondary" className="game-outcome-badge" style={{ animationDelay: '60ms' } as CSSProperties}>
          <RefreshCcw className="size-3.5" />
          Free play
        </Badge>
      ) : passed ? (
        <Badge
          variant="default"
          className="game-outcome-badge game-outcome-badge--gold"
          style={{ animationDelay: '60ms' } as CSSProperties}
        >
          <DoorOpen className="size-3.5" />
          Challenge unlocked
        </Badge>
      ) : null}
      {run.library_opened ? (
        <Badge variant="secondary" className="game-outcome-badge" style={{ animationDelay: '120ms' } as CSSProperties}>
          <BookOpen className="size-3.5" />
          Library used
        </Badge>
      ) : null}
    </>
  )

  const retryAction = (
    <Button
      type="button"
      variant={wonBelowPerfect || !handleNextLevel ? 'default' : 'secondary'}
      disabled={isNavigating}
      onClick={onRestart}
    >
      <RefreshCcw data-icon="inline-start" />
      {isRestarting ? 'Starting fresh run' : playAgainLabel}
    </Button>
  )

  const actions = (
    <>
      {wonBelowPerfect ? retryAction : null}
      {handleNextLevel ? (
        <Button
          type="button"
          onClick={handleNextLevel}
          disabled={isNavigating}
          variant={wonBelowPerfect ? 'secondary' : 'default'}
          title={`Start ${run.next_level?.title ?? 'next level'}`}
        >
          <ArrowRight data-icon="inline-start" />
          {isOpeningNextLevel ? 'Opening next level' : 'Next level'}
        </Button>
      ) : null}
      {onBackToMap ? (
        <Button type="button" variant="ghost" disabled={isNavigating} onClick={onBackToMap}>
          <Castle data-icon="inline-start" />
          Back to Map
        </Button>
      ) : null}
      {wonBelowPerfect ? null : retryAction}
    </>
  )

  return (
    <GameOutcomeModal
      open={open}
      onClose={onClose}
      title={`${headline} - ${runTitle}`}
      tone={isFailed ? 'failure' : 'success'}
      icon={isFailed ? XCircle : Sparkles}
      resultLabel={isFailed ? 'Game Over' : 'You Won'}
      stars={run.stars}
      badges={badges}
      headline={headline}
      message={message}
      stats={stats}
      actions={actions}
    >
      <div className="game-outcome-mastery-panel mt-3 overflow-hidden rounded-xl border border-border/50">
        <button
          type="button"
          className="game-outcome-mastery-panel-head flex w-full items-center gap-1.5 border-b border-border/50 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground"
          title={masteryExpanded ? 'Collapse Command Mastery' : 'View Command Mastery'}
          aria-expanded={masteryExpanded}
          onClick={() => setMasteryExpanded((expanded) => !expanded)}
        >
          <Trophy className="size-3" />
          Command mastery
          <span className="font-mono text-[11px] text-muted-foreground/70">
            ({run.mastery.commands_mastered}/{run.mastery.total_commands})
          </span>
          <ChevronDown
            aria-hidden="true"
            className={cn('ml-auto size-3.5 transition-transform duration-200', masteryExpanded && 'rotate-180')}
          />
        </button>
        {masteryExpanded ? (
          <ul className="game-outcome-mastery-list divide-y divide-border/40">
            {commands.map((command) => {
              const state = command.mastered ? 'mastered' : command.introduced ? 'progress' : 'untried'
              return (
                <li key={command.form_id} className="flex items-center justify-between gap-3 px-3 py-1 text-sm">
                  <CheckCircle2
                    aria-hidden="true"
                    className={cn(
                      'size-4 shrink-0',
                      state === 'mastered' ? 'text-primary' : 'text-muted-foreground/40',
                    )}
                  />
                  <span className="min-w-0 flex-1 truncate text-left font-medium text-foreground">{command.title}</span>
                  <span className="shrink-0 font-mono text-xs text-muted-foreground">
                    {command.strength}/{command.mastered_bar}
                  </span>
                  <span
                    className={cn(
                      'shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold',
                      state === 'mastered' && 'game-outcome-pill-mastered',
                      state === 'progress' && 'bg-warning/15 text-warning',
                      state === 'untried' && 'bg-border/40 text-muted-foreground',
                    )}
                  >
                    {state === 'mastered' ? 'Mastered' : state === 'progress' ? 'In progress' : 'Untried'}
                  </span>
                </li>
              )
            })}
          </ul>
        ) : null}
      </div>
    </GameOutcomeModal>
  )
}
