import type { QueryClient } from '@tanstack/react-query'

import { tierRunsApi } from '@/features/story-map/api/tierRunsApi'
import type { TierCommandResponse, TierRun, TierStepLog } from '@/features/story-map/components/tierWorkspaceTypes'
import { invalidateTierProgressQueries, syncTierRunInCache, updateTierRunCache } from '@/features/story-map/utils/tierRunCache'
import { queryKeys } from '@/shared/api/queryKeys'
import type { MutableRepositoryState } from '@/shared/git/simulator/types'
import { createErrorStep as makeErrorStep, createPendingStep as makePendingStep } from '@/shared/level/terminalSteps'
import type { RepositorySnapshot } from '@/shared/level/types'
import { mergeRepositoryState } from '@/shared/level-runtime/repositoryState'
import { useOptimisticGitCommand } from '@/shared/level-runtime/useOptimisticGitCommand'

const tierStepExtras = () => ({ command_classification: '', contextual_feedback: '', created_at: new Date().toISOString() })
function createPendingStep(command: string, id: number): TierStepLog { return { ...makePendingStep(command, id), ...tierStepExtras() } }
function createLocalStep(command: string, output: string, id: number): TierStepLog {
  return { id, command_text: command, terminal_output: output, result_category: 'Local', ...tierStepExtras() }
}
function createErrorStep(command: string, message: string, id: number): TierStepLog { return { ...makeErrorStep(command, message, id), ...tierStepExtras() } }
function applyOptimisticState(run: TierRun, repositoryState: RepositorySnapshot, steps: TierStepLog[]): TierRun {
  return { ...run, repository_state: repositoryState, steps }
}
function replaceSteps(run: TierRun, steps: TierStepLog[]): TierRun { return { ...run, steps } }

function applyResponse(queryClient: QueryClient, response: TierCommandResponse) {
  const updatedRun = mergeCommandStepIntoRun(queryClient, response)
  updateTierRunCache(queryClient, updatedRun)
  if (!response.run.replay && response.run.status !== 'started') {
    syncTierRunInCache(queryClient, updatedRun)
    invalidateTierProgressQueries(queryClient)
  }
}

export function useTierCommandSubmission(runId: number) {
  const key = queryKeys.adventureTierRun(runId)
  return useOptimisticGitCommand<TierRun, TierStepLog, TierCommandResponse>({
    queryKey: key,
    readSession: (run) => ({ repositoryState: run.repository_state as MutableRepositoryState, revision: run.counts.total_attempts, steps: run.steps }),
    applyOptimisticState,
    replaceSteps,
    createPendingStep,
    createLocalStep,
    createErrorStep,
    submit: (command, execution) => tierRunsApi.submitCommand(runId, command, execution),
    onSuccess: (response, _previous, queryClient) => applyResponse(queryClient, response),
    noSessionMessage: 'No adventure tier run is available to execute this command.',
  })
}

function mergeCommandStepIntoRun(queryClient: QueryClient, response: TierCommandResponse): TierRun {
  const previous = queryClient.getQueryData<TierRun>(queryKeys.adventureTierRun(response.run.id))
  const priorSteps = (previous?.steps ?? []).filter((step) => step.id >= 0)
  const step = {
    id: response.step.id,
    command_text: response.step.command_text,
    terminal_output: response.step.terminal_output,
    result_category: response.step.result_category,
    command_classification: response.step.command_classification,
    contextual_feedback: response.step.contextual_feedback,
    created_at: response.step.created_at,
  }
  const hasCompletion = Object.prototype.hasOwnProperty.call(response.run, 'completion')
  const hasNextDifficulty = Object.prototype.hasOwnProperty.call(response.run, 'next_difficulty')
  const run: TierRun = previous ? {
    ...previous,
    ...response.run,
    counts: { ...previous.counts, ...response.run.counts },
    repository_state: mergeRepositoryState(previous.repository_state, response.run.repository_state),
    progress: response.run.progress ?? previous.progress,
    completion: hasCompletion ? response.run.completion ?? null : previous.completion,
    next_difficulty: hasNextDifficulty ? response.run.next_difficulty ?? null : previous.next_difficulty,
  } : (response.run as TierRun)
  return { ...run, steps: priorSteps.some((item) => item.id === step.id) ? priorSteps : [...priorSteps, step] }
}
