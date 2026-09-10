import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { AppErrorBoundary } from '@/app/AppErrorBoundary'
import { AppProviders } from '@/app/providers'
import { initializePreferences } from '@/shared/preferences/preferences'
import '@/styles/globals.css'
import '@/styles/features/game-outcome.css'
import '@/styles/features/ambient.css'
import '@/styles/features/companion-loader.css'
import '@/styles/features/panels-stats.css'
import '@/styles/features/story-map-viewer.css'
import '@/styles/features/story-map.css'
import '@/styles/features/shared-effects.css'
import '@/styles/features/home.css'
import '@/styles/features/battle.css'
import '@/styles/features/battle/workspace-project-tree.css'
import '@/styles/features/authoring.css'
import '@/styles/features/shop.css'
import '@/styles/features/auth.css'
import '@/styles/features/settings.css'
import '@/styles/features/onboarding.css'
import '@/styles/features/performance.css'
import '@/styles/features/ai-chatbot.css'

initializePreferences()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppErrorBoundary>
      <AppProviders>
        <App />
      </AppProviders>
    </AppErrorBoundary>
  </StrictMode>,
)
