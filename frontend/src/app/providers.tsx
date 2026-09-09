import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Toaster } from 'sonner'

import { subscribeToChallengeRunSync } from '@/features/challenges/utils/challengeRunCache'
import { subscribeToTierRunSync } from '@/features/story-map/utils/tierRunCache'
import { ApiError } from '@/shared/api/apiError'
import { bindBattleAudioVisibility, bindButtonSoundEffects } from '@/shared/audio/battleAudio'
import { PreferencesSync } from '@/shared/preferences/PreferencesSync'

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: (failureCount, error) => {
              if (error instanceof ApiError && error.status < 500) return false
              return failureCount < 1
            },
            refetchOnWindowFocus: false,
          },
        },
      }),
  )

  useEffect(() => subscribeToChallengeRunSync(queryClient), [queryClient])
  useEffect(() => subscribeToTierRunSync(queryClient), [queryClient])
  useEffect(() => bindButtonSoundEffects(), [])
  useEffect(() => bindBattleAudioVisibility(), [])

  return (
    <QueryClientProvider client={queryClient}>
      <PreferencesSync />
      {children}
      <Toaster position="bottom-right" expand={false} />
    </QueryClientProvider>
  )
}
