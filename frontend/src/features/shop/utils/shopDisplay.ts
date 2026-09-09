import { BookOpen, User, type LucideIcon } from 'lucide-react'
import type { QueryClient } from '@tanstack/react-query'

import { queryKeyRoots, queryKeys } from '@/shared/api/queryKeys'
import type { ShopDisplayItem } from '@/shared/shop/model/shopPresentation'

export type ShopTab = 'stories' | 'companions'

export type ShopTabConfig = {
  id: ShopTab
  label: string
  description: string
  Icon: LucideIcon
}

export const shopTabs: ShopTabConfig[] = [
  { id: 'stories', label: 'Stories', description: 'World bundles', Icon: BookOpen },
  { id: 'companions', label: 'Companions', description: 'Adventurers', Icon: User },
]

export function formatCoins(value: number) {
  return value.toLocaleString()
}

export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'The shop action failed.'
}

export function isShopTab(value: string | null): value is ShopTab {
  return value === 'stories' || value === 'companions'
}

export function actionLabel(item: ShopDisplayItem, balance: number, walletPending: boolean) {
  if (item.owned && item.kind === 'story') return 'View in Stories'
  if (item.owned && item.kind === 'companion') return 'Manage in Loadout'
  if (item.price === 0) return 'Claim'
  if (!walletPending && item.price > balance) return `Need ${formatCoins(item.price - balance)} more`
  return 'Purchase'
}

export function actionDisabled(
  item: ShopDisplayItem,
  pending: boolean,
  balance: number,
  walletPending: boolean,
  purchasesEnabled = true,
) {
  return (
    pending
    || (!item.owned && !purchasesEnabled)
    || (!item.owned && item.price > 0 && !walletPending && item.price > balance)
  )
}

/**
 * A story purchase can flip chapter lock state immediately (no run to wait
 * on), so the chapter/overview queries that render lock UI need the same
 * invalidation the run-completion flows already do (see
 * invalidateLevelProgressQueries / invalidateTierProgressQueries) - otherwise
 * the story map keeps serving pre-purchase cached data until its staleTime
 * elapses or a hard refresh happens.
 */
export function invalidateShopUnlockQueries(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: queryKeys.chapters })
  void queryClient.invalidateQueries({ queryKey: queryKeyRoots.chapterOverview })
  void queryClient.invalidateQueries({ queryKey: queryKeys.stories })
  void queryClient.invalidateQueries({ queryKey: queryKeys.homeSummary })
  void queryClient.invalidateQueries({ queryKey: queryKeys.statsSummary })
}
