import type { QueryClient } from '@tanstack/react-query'

import { writeTierRunBootstrap } from '@/features/story-map/utils/tierRunBootstrap'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import { queryKeyRoots, queryKeys } from '@/shared/api/queryKeys'

const tierRunSyncChannel = 'git-it:adventure-tier-run-sync'

type TierRunSyncMessage = {
  type: 'adventure-tier-run-updated'
  run: TierRun
}

export function syncTierRunInCache(
  queryClient: QueryClient,
  run: TierRun,
  options: { broadcast?: boolean } = {},
) {
  updateTierRunCache(queryClient, run)
  if (options.broadcast !== false && !run.replay) {
    broadcastTierRunSync(run)
  }

  invalidateTierProgressQueries(queryClient)
}

export function updateTierRunCache(queryClient: QueryClient, run: TierRun) {
  writeTierRunBootstrap(run)
  queryClient.setQueryData(queryKeys.adventureTierRun(run.id), run)
}

export function subscribeToTierRunSync(queryClient: QueryClient) {
  if (typeof window === 'undefined') return () => {}

  const handleMessage = (message: unknown) => {
    if (!isTierRunSyncMessage(message)) return
    syncTierRunInCache(queryClient, message.run, { broadcast: false })
  }

  const channel = typeof BroadcastChannel !== 'undefined'
    ? new BroadcastChannel(tierRunSyncChannel)
    : null
  const handleBroadcastMessage = (event: MessageEvent<unknown>) => handleMessage(event.data)
  channel?.addEventListener('message', handleBroadcastMessage)

  const handleStorage = (event: StorageEvent) => {
    if (event.key !== tierRunSyncChannel || !event.newValue) return
    try {
      handleMessage(JSON.parse(event.newValue))
    } catch {
      // Ignore malformed cross-tab messages.
    }
  }
  window.addEventListener('storage', handleStorage)

  return () => {
    channel?.removeEventListener('message', handleBroadcastMessage)
    channel?.close()
    window.removeEventListener('storage', handleStorage)
  }
}

export function invalidateTierProgressQueries(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.chapters })
  void queryClient.invalidateQueries({ queryKey: queryKeys.homeSummary })
  void queryClient.invalidateQueries({ queryKey: queryKeys.statsSummary })
  void queryClient.invalidateQueries({ queryKey: queryKeys.performanceSummary })
  void queryClient.invalidateQueries({ queryKey: queryKeyRoots.chapterOverview })
  void queryClient.invalidateQueries({ queryKey: queryKeys.learnedSkills })
  void queryClient.invalidateQueries({ queryKey: queryKeys.wallet })
}

function broadcastTierRunSync(run: TierRun) {
  if (typeof window === 'undefined') return
  const message: TierRunSyncMessage = {
    type: 'adventure-tier-run-updated',
    run,
  }
  if (typeof BroadcastChannel !== 'undefined') {
    const channel = new BroadcastChannel(tierRunSyncChannel)
    channel.postMessage(message)
    channel.close()
  }
  try {
    window.localStorage.setItem(
      tierRunSyncChannel,
      JSON.stringify({ ...message, sentAt: Date.now() }),
    )
  } catch {
    // Some browsers disable storage; BroadcastChannel is enough when available.
  }
}

function isTierRunSyncMessage(value: unknown): value is TierRunSyncMessage {
  if (!value || typeof value !== 'object') return false
  const message = value as Partial<TierRunSyncMessage>
  return message.type === 'adventure-tier-run-updated' && Boolean(message.run)
}
