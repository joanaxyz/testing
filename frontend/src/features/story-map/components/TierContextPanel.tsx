import { Smile, Target, TerminalSquare } from 'lucide-react'

import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import {
  DifficultyChip,
  type LevelContextTag,
  type LevelFact,
  LevelStoryCard,
  StarTriplet,
} from '@/shared/level/components/LevelContextPanel'
import { RookIcon, StarSolidIcon } from '@/shared/level/components/workspaceIcons'
import { hasLevelContext, normalizeLevelContext } from '@/shared/level/utils/levelContext'

export function TierContextPanel({ run }: { run: TierRun }) {
  const context = contextForRun(run)
  const facts: LevelFact[] = [
    {
      label: 'Mode',
      icon: RookIcon,
      value: `Adventure${run.replay ? ' · Replay' : ''}`,
    },
    ...(run.difficulty
      ? [{ label: 'Difficulty', icon: Smile, value: <DifficultyChip difficulty={run.difficulty} /> }]
      : []),
    {
      label: 'Stars',
      icon: StarSolidIcon,
      iconClass: 'lvlctx-icon--amber',
      value: <StarTriplet count={run.stars || 0} />,
    },
    {
      label: 'Commands',
      icon: TerminalSquare,
      value: (
        <span className="lvlctx-num" data-tour-target="command-budget">
          {run.counts.counted_action_total} / {run.policy.max_counted_commands}
        </span>
      ),
    },
    {
      label: 'Star target',
      icon: Target,
      value: (
        <span className="lvlctx-num" data-tour-target="star-budget">
          ≤ {run.policy.min_counted_commands} {run.policy.min_counted_commands === 1 ? 'command' : 'commands'}
        </span>
      ),
    },
  ]

  const tags: LevelContextTag[] = [
    ...(run.chapter ? [{ label: `Module ${run.chapter.number}`, variant: 'blue' as const }] : []),
    ...(run.difficulty
      ? [
          {
            label: run.difficulty.charAt(0).toUpperCase() + run.difficulty.slice(1),
            variant: 'default' as const,
          },
        ]
      : []),
    ...(run.variant.changed_variant
      ? [{ label: 'Changed variant', variant: 'warning' as const }]
      : []),
  ]

  return (
    <LevelStoryCard
      title={run.tier.adventure_level_title}
      context={context}
      facts={facts}
      tags={tags}
      labels={{
        story: 'Scenario',
        task: 'Objective',
      }}
      showHeader={false}
      tourTarget="tier-brief"
    />
  )
}

// Legacy tier content puts the case-specific narrative in scenario_context's
// details (a single unlabeled entry - see seed_legacy_modules.py), while
// `story` only ever holds the generic wave-level brief. The scenario brief a
// player actually needs is that per-case narrative, so it takes over the
// Scenario section instead of rendering as a separate "Required Values"
// copy-chip section (there are no literal copyable values for tiers, unlike
// Challenges).
function contextForRun(run: TierRun) {
  const context = normalizeLevelContext(run.scenario_context)
  const narrative = context.details[0]?.value
  const fallback = normalizeLevelContext({
    story: '',
    task: '',
  })
  const resolved = hasLevelContext(context) ? context : fallback

  return { ...resolved, story: narrative || resolved.story, details: [] }
}
