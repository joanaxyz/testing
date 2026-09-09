import type { QueryClient } from '@tanstack/react-query'

import { useTierCommandSubmission } from '@/features/story-map/hooks/useTierCommandSubmission'
import type { TierDagAnimationController } from '@/features/story-map/hooks/useTierDagAnimation'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import { stringList } from '@/features/story-map/components/tierWorkspaceLayout'
import { queryKeys } from '@/shared/api/queryKeys'
import { isExitCommand } from '@/shared/level-runtime/commands'

export function createTierWorkspaceCommandHandler({
  runId,
  mutation,
  dagAnimation,
  queryClient,
  clearToast,
  evaluateAndNotify,
  setExitConfirmOpen,
  setWorkspaceEditorPath,
  queueOutcomeAnimation,
}: {
  runId: number
  mutation: ReturnType<typeof useTierCommandSubmission>
  dagAnimation: TierDagAnimationController
  queryClient: QueryClient
  clearToast: () => void
  evaluateAndNotify: (
    run: TierRun,
    commandClassification: string,
    onExitSuggested: () => void,
  ) => void
  setExitConfirmOpen: (open: boolean) => void
  setWorkspaceEditorPath: (path: string | null) => void
  queueOutcomeAnimation: (runId: number) => void
}) {
  return (command: string) => {
    if (mutation.isPending) return
    if (isExitCommand(command)) {
      setExitConfirmOpen(true)
      return
    }

    clearToast()
    dagAnimation.onCommandStart()

    mutation.mutate(command, {
      onSuccess: (response) => {
        dagAnimation.onCommandResolved(response.command_outcome)
        if (response.run.status === 'completed' || response.run.status === 'failed') {
          queueOutcomeAnimation(response.run.id)
        }

        if (response.command_family === 'mergetool') {
          const snapshot = response.run.repository_state
          const requestedPaths = stringList(snapshot.operation_metadata?.last_mergetool_paths)
          const conflictPaths = snapshot.conflicts ?? []
          const nextPath = requestedPaths.find((path) => conflictPaths.includes(path)) ?? conflictPaths[0]
          if (nextPath) setWorkspaceEditorPath(nextPath)
        }

        if (!response.run.replay) {
          const updatedRun = queryClient.getQueryData<TierRun>(queryKeys.adventureTierRun(runId))
          if (updatedRun) {
            evaluateAndNotify(
              updatedRun,
              response.step.command_classification,
              () => {
                setExitConfirmOpen(true)
              },
            )
          }
        }
      },
      onError: () => dagAnimation.onCommandError(),
    })
  }
}
