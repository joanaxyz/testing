import type {
  LevelScenarioContext,
  RepositorySnapshot,
  RepositoryVisualization,
} from '@/shared/level/types'
import type { ApiSchemas } from '@/shared/api/generated/apiTypes'
import type { CommandSubmissionOutcome } from '@/shared/level-runtime/commandOutcome'

export type TierDifficulty = 'easy' | 'medium' | 'hard'

type TierRef = {
  id: number
  difficulty: TierDifficulty
  adventure_level_id: number
  adventure_level_slug: string
  adventure_level_title: string
}

type TierRunStepResponse = Omit<
  ApiSchemas['AdventureLevelTierRunStepResponse'],
  'visualization_snapshot'
> & {
  visualization_snapshot: RepositoryVisualization
}

type TierOptimisticStep = Omit<TierRunStepResponse, 'visualization_snapshot'> & {
  visualization_snapshot?: never
}

export type TierStepLog = TierRunStepResponse | TierOptimisticStep

type TierRunRefinementKeys =
  | 'tier'
  | 'scenario_context'
  | 'chapter'
  | 'story'
  | 'variant'
  | 'progress'
  | 'policy'
  | 'counts'
  | 'scaffolding'
  | 'repository_state'
  | 'visualization'
  | 'expected_state'
  | 'steps'
  | 'next_difficulty'
  | 'completion'

export type TierRunResponse = Omit<
  ApiSchemas['AdventureLevelTierRunResponse'],
  TierRunRefinementKeys
> & {
  tier: TierRef
  scenario_context: LevelScenarioContext
  chapter: { id: number; number: number; title: string } | null
  story: { id: number; slug: string; title: string; world_slug: string } | null
  variant: {
    id: number
    label: string
    changed_variant: boolean
  }
  progress: {
    completed: number
    total: number
    cleared: boolean
  }
  policy: {
    min_counted_commands: number
    max_counted_commands: number
  }
  counts: {
    counted_action_total: number
    minimum_counted_commands: number
    maximum_counted_commands: number
    non_counted_diagnostic_total: number
    remaining_counted_commands: number
    max_reached: boolean
    total_attempts: number
  }
  scaffolding: {
    live_dag: boolean
    expected_state: boolean
    contextual_feedback: boolean
  }
  repository_state: RepositorySnapshot
  visualization: RepositoryVisualization
  expected_state: RepositorySnapshot | null
  steps: TierRunStepResponse[]
  next_difficulty: {
    id: number
    difficulty: TierDifficulty
  } | null
  completion: { stars: number; counted_action_total: number; completed_at: string } | null
}

export type TierRun = Omit<TierRunResponse, 'steps'> & {
  steps: TierStepLog[]
}

/** Mirrors RESULT_TARGET_MATCHED in common/constants.py - shared with challenges/types.ts. */
export const TIER_RESULT_TARGET_MATCHED = 'TargetMatched'

type TierCommandStep = Omit<
  ApiSchemas['AdventureLevelTierCommandStepResponse'],
  'visualization_snapshot'
> & {
  visualization_snapshot: RepositoryVisualization
}

export type TierCommandResponse = Omit<
  ApiSchemas['AdventureLevelTierCommandResponse'],
  'run' | 'command_outcome' | 'step'
> & {
  run: TierRunUpdate
  command_outcome: CommandSubmissionOutcome
  step: TierCommandStep
}

type TierRunUpdate = Omit<
  ApiSchemas['AdventureLevelTierCommandRunResponse'],
  'counts' | 'repository_state' | 'visualization' | 'progress' | 'completion' | 'next_difficulty'
> & {
  counts: TierRun['counts']
  repository_state: RepositorySnapshot
  visualization: RepositoryVisualization
  progress?: TierRun['progress']
  completion?: TierRun['completion']
  next_difficulty?: TierRun['next_difficulty']
}
