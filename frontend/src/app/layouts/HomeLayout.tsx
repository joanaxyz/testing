import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'

import { startBackgroundMusic, stopBackgroundMusic } from '@/shared/audio/battleAudio'
import { CursorGlow } from '@/shared/components/CursorGlow'
import { OnboardingProvider } from '@/features/onboarding/OnboardingProvider'
import { AIChatbot } from '@/features/ai-support/components/AIChatbot'
import { useAuthStore } from '@/shared/auth/useAuth'
import { AppMobileNav, AppTopbar } from '@/shared/navigation/AppNavigation'
import { isStoryMapRoute } from '@/shared/navigation/routes'
import { cn } from '@/shared/utils/cn'

export function HomeLayout() {
  const userId = useAuthStore((state) => state.user?.id)
  const location = useLocation()
  const isStoryMapPage = isStoryMapRoute(location.pathname)
  const isAuthoringPage = location.pathname.startsWith('/level-editor')

  useEffect(() => {
    startBackgroundMusic('outside')
    return () => stopBackgroundMusic('outside')
  }, [])

  return (
    <div className="app-shell">
      <a className="skip-link" href="#app-main-content">Skip to content</a>
      <CursorGlow />
      <AppTopbar
        className={cn(
          isAuthoringPage && 'home-workspace-header',
        )}
      />
      <main id="app-main-content" tabIndex={-1} className={cn('app-main', isStoryMapPage && 'app-main--story-map')}>
        <OnboardingProvider key={userId ?? 'guest'} userId={userId}>
          <Outlet />
        </OnboardingProvider>
      </main>
      <AppMobileNav />
      <AIChatbot />
    </div>
  )
}
