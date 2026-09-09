import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import { tierRunsApi } from '@/features/story-map/api/tierRunsApi'
import { syncTierRunInCache } from '@/features/story-map/utils/tierRunCache'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import { ErrorState } from '@/shared/components/ErrorState'
import { LoadingState } from '@/shared/components/LoadingState'

type TierStartMode = 'start' | 'replay' | 'retry'

const loadingCopy: Record<TierStartMode, { label: string; description: string }> = {
  start: {
    label: 'Starting adventure',
    description: 'Preparing the repository, terminal, and adventure workspace.',
  },
  replay: {
    label: 'Starting replay',
    description: 'Preparing an uncounted replay of this adventure.',
  },
  retry: {
    label: 'Retrying adventure',
    description: 'Resetting the repository and preparing a fresh attempt.',
  },
}

/** Mirrors ChallengeStartPage.tsx for the adventure-tier run lifecycle. */
export function TierStartPage({ mode = 'start' }: { mode?: TierStartMode }) {
  const { tierId, runId } = useParams<{ tierId?: string; runId?: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const targetId = Number(mode === 'retry' ? runId : tierId)

  const start = useMutation({
    mutationFn: async (): Promise<TierRun> => {
      if (!Number.isFinite(targetId)) {
        throw new Error(mode === 'retry' ? 'Missing adventure tier run.' : 'Missing adventure tier.')
      }
      if (mode === 'retry') return tierRunsApi.retryRun(targetId)
      return tierRunsApi.startRun(targetId, { replay: mode === 'replay' })
    },
    onSuccess: (run) => {
      syncTierRunInCache(queryClient, run)
      navigate(`/adventure-tier-runs/${run.id}`, { replace: true })
    },
  })

  useEffect(() => {
    if (start.isIdle) {
      start.mutate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (start.isError) {
    return (
      <div className="grid min-h-screen place-items-center bg-background p-6">
        <ErrorState title="Could not prepare adventure" description={start.error.message} />
      </div>
    )
  }

  const copy = loadingCopy[mode]
  return <LoadingState description={copy.description} label={copy.label} showCompanion={false} variant="screen" />
}
