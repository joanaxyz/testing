import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo } from 'react'

import { tierRunsApi } from '@/features/story-map/api/tierRunsApi'
import {
  clearTierRunBootstrap,
  readTierRunBootstrap,
} from '@/features/story-map/utils/tierRunBootstrap'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import type { TerminalLine } from '@/shared/level/types'
import { isEphemeralStep, terminalLinesFromSteps } from '@/shared/level/terminalSteps'
import { queryKeys } from '@/shared/api/queryKeys'

const bootLines: TerminalLine[] = []

export function useTierRun(runId: number) {
  const queryClient = useQueryClient()
  const bootstrapRun = Number.isFinite(runId) ? readTierRunBootstrap(runId) : undefined
  const cachedRun = Number.isFinite(runId)
    ? queryClient.getQueryData<TierRun>(queryKeys.adventureTierRun(runId))
    : undefined
  const initialRun = cachedRun ?? bootstrapRun

  const query = useQuery({
    queryKey: queryKeys.adventureTierRun(runId),
    queryFn: async () => {
      const run = await tierRunsApi.getRun(runId)
      clearTierRunBootstrap(runId)
      return run
    },
    enabled: Number.isFinite(runId),
    initialData: initialRun,
    staleTime: 30_000,
  })

  const run = query.data ?? null
  const lines = useMemo(() => (run ? terminalLinesFromSteps(run.steps ?? []) : bootLines), [run])
  const feedback = run?.steps?.filter((step) => !isEphemeralStep(step)).at(-1)?.contextual_feedback ?? ''

  return {
    query,
    run,
    lines,
    feedback,
  }
}
