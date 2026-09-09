import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type { NavigateFunction } from 'react-router-dom'
import { useMutation, type QueryClient } from '@tanstack/react-query'

import { tierRunsApi } from '@/features/story-map/api/tierRunsApi'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import {
  invalidateTierProgressQueries,
  syncTierRunInCache,
  updateTierRunCache,
} from '@/features/story-map/utils/tierRunCache'
import { mapUrlForRun } from '@/features/story-map/components/tierWorkspaceLayout'
import { queryKeys } from '@/shared/api/queryKeys'
import type {
  WorkspaceFileInput,
  WorkspaceFileRenameInput,
} from '@/shared/level/workspaceFileTypes'

export function useTierWorkspaceMutations({
  run,
  runId,
  navigate,
  queryClient,
  latestRunRef,
  bypassNavigationRunId,
  setExitNavigationRunId,
  setExitConfirmOpen,
  setStartOverConfirmOpen,
  setDismissedCompletionRunId,
}: {
  run: TierRun | null
  runId: number
  navigate: NavigateFunction
  queryClient: QueryClient
  latestRunRef: MutableRefObject<TierRun | null>
  bypassNavigationRunId: MutableRefObject<number | null>
  setExitNavigationRunId: Dispatch<SetStateAction<number | null>>
  setExitConfirmOpen: Dispatch<SetStateAction<boolean>>
  setStartOverConfirmOpen: Dispatch<SetStateAction<boolean>>
  setDismissedCompletionRunId: Dispatch<SetStateAction<number | null>>
}) {
  const exitMutation = useMutation({
    onMutate: () => {
      const latestRun = latestRunRef.current ?? run
      bypassNavigationRunId.current = latestRun?.id ?? runId
      setExitNavigationRunId(latestRun?.id ?? runId)
      setExitConfirmOpen(false)
    },
    mutationFn: async () => {
      if (!run) throw new Error('No adventure tier run is available to exit.')
      if (run.status === 'started') await tierRunsApi.discardRun(run.id)
      return run
    },
    onSuccess: (exitedRun) => {
      navigate(mapUrlForRun(exitedRun), { replace: true })
      window.setTimeout(() => {
        if (exitedRun.status === 'started') {
          queryClient.removeQueries({ queryKey: queryKeys.adventureTierRun(exitedRun.id) })
        } else {
          syncTierRunInCache(queryClient, exitedRun)
        }
        invalidateTierProgressQueries(queryClient)
      }, 0)
    },
    onError: () => {
      bypassNavigationRunId.current = null
      setExitNavigationRunId(null)
    },
  })

  const replayMutation = useMutation({
    mutationFn: (tierId: number) => tierRunsApi.startRun(tierId, { replay: true }),
    onSuccess: (next) => {
      moveToReplacementRun({
        previousRun: run,
        nextRun: next,
        navigate,
        queryClient,
        bypassNavigationRunId,
        setExitNavigationRunId,
        setExitConfirmOpen,
        setStartOverConfirmOpen,
        setDismissedCompletionRunId,
      })
    },
  })

  const startLevelMutation = useMutation({
    mutationFn: (tierId: number) => tierRunsApi.startRun(tierId),
    onSuccess: (next) => {
      syncTierRunInCache(queryClient, next)
      invalidateTierProgressQueries(queryClient)
      if (run?.status === 'completed') setDismissedCompletionRunId(run.id)
      navigate(`/adventure-tier-runs/${next.id}`)
    },
  })

  // Continues the SAME tier after a partial clear (progress not yet at
  // required_successful_attempts) - passes prior_run_id so
  // TierVariantSelectionService rotates away from the just-played variant
  // instead of defaulting to variants[0] every time.
  const continueMutation = useMutation({
    mutationFn: () => {
      if (!run) throw new Error('No adventure tier run is available to continue.')
      return tierRunsApi.startRun(run.tier.id, { prior_run_id: run.id })
    },
    onSuccess: (next) => {
      syncTierRunInCache(queryClient, next)
      invalidateTierProgressQueries(queryClient)
      if (run?.status === 'completed') setDismissedCompletionRunId(run.id)
      navigate(`/adventure-tier-runs/${next.id}`)
    },
  })

  const retryMutation = useMutation({
    mutationFn: () => {
      if (!run) throw new Error('No adventure tier run is available to retry.')
      return tierRunsApi.retryRun(run.id)
    },
    onSuccess: (next) => {
      moveToReplacementRun({
        previousRun: run,
        nextRun: next,
        navigate,
        queryClient,
        bypassNavigationRunId,
        setExitNavigationRunId,
        setExitConfirmOpen,
        setStartOverConfirmOpen,
        setDismissedCompletionRunId,
      })
    },
  })

  const createFileMutation = useMutation({
    mutationFn: (input: WorkspaceFileInput) => {
      if (!run) throw new Error('No adventure tier run is available to update.')
      return tierRunsApi.createFile(run.id, input)
    },
    onSuccess: (updatedRun) => {
      updateTierRunCache(queryClient, updatedRun)
    },
  })

  const writeFileMutation = useMutation({
    mutationFn: (input: WorkspaceFileInput) => {
      if (!run) throw new Error('No adventure tier run is available to update.')
      return tierRunsApi.writeFile(run.id, input)
    },
    onSuccess: (updatedRun) => {
      updateTierRunCache(queryClient, updatedRun)
    },
  })

  const renameFileMutation = useMutation({
    mutationFn: (input: WorkspaceFileRenameInput) => {
      if (!run) throw new Error('No adventure tier run is available to update.')
      return tierRunsApi.renameFile(run.id, input)
    },
    onSuccess: (updatedRun) => {
      updateTierRunCache(queryClient, updatedRun)
    },
  })

  const deleteFileMutation = useMutation({
    mutationFn: (path: string) => {
      if (!run) throw new Error('No adventure tier run is available to update.')
      return tierRunsApi.deleteFile(run.id, path)
    },
    onSuccess: (updatedRun) => {
      updateTierRunCache(queryClient, updatedRun)
    },
  })

  const startFreshAttempt = () => retryMutation.mutate()
  const playAgain = () => {
    if (run?.replay) {
      replayMutation.mutate(run.tier.id)
    } else {
      retryMutation.mutate()
    }
  }

  return {
    exitMutation,
    startLevelMutation,
    continueMutation,
    replayMutation,
    retryMutation,
    createFileMutation,
    writeFileMutation,
    renameFileMutation,
    deleteFileMutation,
    startFreshAttempt,
    playAgain,
  }
}

function moveToReplacementRun({
  previousRun,
  nextRun,
  navigate,
  queryClient,
  bypassNavigationRunId,
  setExitNavigationRunId,
  setExitConfirmOpen,
  setStartOverConfirmOpen,
  setDismissedCompletionRunId,
}: {
  previousRun: TierRun | null
  nextRun: TierRun
  navigate: NavigateFunction
  queryClient: QueryClient
  bypassNavigationRunId: MutableRefObject<number | null>
  setExitNavigationRunId: Dispatch<SetStateAction<number | null>>
  setExitConfirmOpen: Dispatch<SetStateAction<boolean>>
  setStartOverConfirmOpen: Dispatch<SetStateAction<boolean>>
  setDismissedCompletionRunId: Dispatch<SetStateAction<number | null>>
}) {
  syncTierRunInCache(queryClient, nextRun)
  invalidateTierProgressQueries(queryClient)
  setDismissedCompletionRunId(null)
  setExitConfirmOpen(false)
  setStartOverConfirmOpen(false)
  if (previousRun?.status === 'started') {
    bypassNavigationRunId.current = previousRun.id
    setExitNavigationRunId(previousRun.id)
  } else {
    bypassNavigationRunId.current = null
    setExitNavigationRunId(null)
  }
  navigate(`/adventure-tier-runs/${nextRun.id}`)
  if (previousRun?.id && previousRun.id !== nextRun.id) {
    window.setTimeout(() => {
      queryClient.removeQueries({ queryKey: queryKeys.adventureTierRun(previousRun.id) })
    }, 0)
  }
}
