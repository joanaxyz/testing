import type { ApiRequestBody } from '@/shared/api/generated/apiTypes'
import { apiOperationRequest } from '@/shared/api/httpClient'
import {
  commandSubmitBody,
  workspaceFileBody,
  workspaceFileRenameBody,
} from '@/shared/level-runtime/runMutationInputs'
import type {
  WorkspaceFileInput,
  WorkspaceFileRenameInput,
} from '@/shared/level/workspaceFileTypes'
import type { CommandExecutionPayload } from '@/shared/level/types'
import type { TierCommandResponse, TierRunResponse } from '@/features/story-map/components/tierWorkspaceTypes'

export const tierRunsApi = {
  startRun(tierId: number, input?: { prior_run_id?: number | null; replay?: boolean }) {
    const body = {
      source_entry_point: 'level_page',
      prior_run_id: input?.prior_run_id ?? null,
      replay: input?.replay ?? false,
    } as ApiRequestBody<'adventure_level_tiers_runs_create'>
    return apiOperationRequest<'adventure_level_tiers_runs_create', TierRunResponse>(
      'adventure_level_tiers_runs_create',
      `/adventure-level-tiers/${tierId}/runs/`,
      { body },
    )
  },
  getRun(runId: number) {
    return apiOperationRequest<'adventure_tier_runs_retrieve', TierRunResponse>(
      'adventure_tier_runs_retrieve',
      `/adventure-tier-runs/${runId}/`,
    )
  },
  submitCommand(runId: number, command: string, execution: CommandExecutionPayload) {
    return apiOperationRequest<'adventure_tier_runs_submit_command_create', TierCommandResponse>(
      'adventure_tier_runs_submit_command_create',
      `/adventure-tier-runs/${runId}/submit-command/`,
      { body: commandSubmitBody(command, execution) },
    )
  },
  retryRun(runId: number) {
    return apiOperationRequest<'adventure_tier_runs_retry_create', TierRunResponse>(
      'adventure_tier_runs_retry_create',
      `/adventure-tier-runs/${runId}/retry/`,
    )
  },
  discardRun(runId: number, options?: Omit<RequestInit, 'method' | 'body'>) {
    return apiOperationRequest(
      'adventure_tier_runs_destroy',
      `/adventure-tier-runs/${runId}/`,
      options,
    )
  },
  createFile(runId: number, input: WorkspaceFileInput) {
    return apiOperationRequest<'adventure_tier_runs_files_create', TierRunResponse>(
      'adventure_tier_runs_files_create',
      `/adventure-tier-runs/${runId}/files/`,
      { body: workspaceFileBody(input) },
    )
  },
  writeFile(runId: number, input: WorkspaceFileInput) {
    return apiOperationRequest<'adventure_tier_runs_files_partial_update', TierRunResponse>(
      'adventure_tier_runs_files_partial_update',
      `/adventure-tier-runs/${runId}/files/`,
      { body: workspaceFileBody(input) },
    )
  },
  renameFile(runId: number, input: WorkspaceFileRenameInput) {
    return apiOperationRequest<'adventure_tier_runs_files_update', TierRunResponse>(
      'adventure_tier_runs_files_update',
      `/adventure-tier-runs/${runId}/files/`,
      { body: workspaceFileRenameBody(input) },
    )
  },
  deleteFile(runId: number, path: string) {
    return apiOperationRequest<'adventure_tier_runs_files_destroy', TierRunResponse>(
      'adventure_tier_runs_files_destroy',
      `/adventure-tier-runs/${runId}/files/?path=${encodeURIComponent(path)}`,
    )
  },
}
