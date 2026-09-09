import { Navigate, Outlet, createBrowserRouter, type RouteObject } from 'react-router-dom'

import { AdminLayout } from '@/features/admin/components/AdminLayout'
import { ADMIN_SECTIONS } from '@/features/admin/utils/adminSections'
import { AuthLayout } from '@/app/layouts/AuthLayout'
import { HomeLayout } from '@/app/layouts/HomeLayout'
import { LevelLayout } from '@/app/layouts/LevelLayout'
import {
  LegacySharedStoryRedirect,
  LegacyStoryEditorRedirect,
  LegacyStoryRouteRedirect,
} from '@/app/LegacyRedirects'
import { Protected } from '@/app/Protected'
import { RequireCompanion } from '@/app/RequireCompanion'
import { ForgotPasswordPage } from '@/features/auth/pages/ForgotPasswordPage'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { RegisterPage } from '@/features/auth/pages/RegisterPage'
import { ResetPasswordPage } from '@/features/auth/pages/ResetPasswordPage'
import { HomePage } from '@/features/home/pages/HomePage'
import { AdventureStartPage } from '@/features/adventures/pages/AdventureStartPage'
import { ChallengeStartPage } from '@/features/challenges/pages/ChallengeStartPage'
import { TierStartPage } from '@/features/story-map/pages/TierStartPage'
import {
  DESIGN_PREVIEW_STORY_MAP_ROUTE,
  ADMIN_ROUTES,
  HOME_ROUTE,
  SHOP_ROUTE,
  STORIES_ROUTE,
  STORY_DETAIL_ROUTE,
  storyPath,
  storyPathWithQuery,
} from '@/shared/navigation/routes'
import {
  LEGACY_ARCHIVE_ROUTE,
  LEGACY_DESIGN_PREVIEW_STORY_ROUTE,
  LEGACY_MY_STORY_ROUTE,
  LEGACY_STORY_ROUTE,
  LEGACY_STORIES_ROUTE,
} from '@/shared/navigation/legacyRoutes'
import { LoadingState } from '@/shared/components/LoadingState'

/**
 * Dev-only design preview: the real Home hub view inside the real layout
 * chrome, fed by fixture data instead of the API (no auth required).
 * `import.meta.env.DEV` is statically false in production builds, so this
 * route - and its lazily imported fixture modules - are compiled away.
 */
const designPreviewRoutes: RouteObject[] = import.meta.env.DEV
  ? [
      {
        element: <HomeLayout />,
        children: [
          {
            path: '/design-preview/home',
            lazy: () => import('@/features/home/preview/HomePreviewPage'),
          },
          {
            path: '/design-preview/shop',
            lazy: async () => ({
              Component: (await import('@/features/shop/pages/ShopPage')).ShopPage,
            }),
          },
        ],
      },
      {
        path: '/dev/battle',
        lazy: () => import('@/features/dev/pages/BattlePlayground'),
      },
      {
        path: '/dev/monster-scales',
        lazy: () => import('@/features/dev/pages/MonsterScalePlayground'),
      },
      {
        path: '/dev/outcomes',
        lazy: () => import('@/features/dev/pages/OutcomePreviewPage'),
      },
      {
        path: DESIGN_PREVIEW_STORY_MAP_ROUTE,
        lazy: () => import('@/features/story-map/pages/StoryMapPreviewPage'),
      },
      { path: LEGACY_DESIGN_PREVIEW_STORY_ROUTE, element: <Navigate replace to={DESIGN_PREVIEW_STORY_MAP_ROUTE} /> },
    ]
  : []

const appRoutes: RouteObject[] = [
  ...designPreviewRoutes,
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/reset-password/:uid/:token', element: <ResetPasswordPage /> },
    ],
  },
  // Legacy shared-map links redirect to the canonical story map.
  { path: `${LEGACY_STORY_ROUTE}/shared/:designId`, element: <Navigate replace to={storyPath()} /> },
  { path: `${LEGACY_ARCHIVE_ROUTE}/shared/:designId`, element: <LegacySharedStoryRedirect /> },
  {
    element: (
      <Protected>
        <HomeLayout />
      </Protected>
    ),
    children: [
      { path: '/', element: <Navigate replace to={storyPath()} /> },
      { path: HOME_ROUTE, element: <HomePage /> },
      // Browsing Home, Stories, and repository-only challenges does not require
      // a companion. Adventure play remains protected below.
      { path: LEGACY_STORY_ROUTE, element: <Navigate replace to={storyPath()} /> },
      { path: LEGACY_STORIES_ROUTE, element: <Navigate replace to={STORIES_ROUTE} /> },
      { path: `${LEGACY_STORIES_ROUTE}/:storySlug`, element: <LegacyStoryRouteRedirect /> },
      {
        path: STORIES_ROUTE,
        lazy: async () => ({
          Component: (await import('@/features/story-map/pages/StorySelectPage')).StorySelectPage,
        }),
      },
      {
        path: STORY_DETAIL_ROUTE,
        lazy: async () => ({
          Component: (await import('@/features/story-map/pages/StoryMapPage')).StoryMapPage,
        }),
      },
      { path: LEGACY_ARCHIVE_ROUTE, element: <Navigate replace to={storyPath()} /> },
      { path: LEGACY_MY_STORY_ROUTE, element: <Navigate replace to={storyPathWithQuery(undefined, 'view=mine')} /> },
      { path: '/gallery', element: <Navigate replace to={HOME_ROUTE} /> },
      { path: '/dashboard', element: <Navigate replace to={HOME_ROUTE} /> },
      { path: '/stats', element: <Navigate replace to={`${HOME_ROUTE}?tab=overview`} /> },
      { path: '/performance', element: <Navigate replace to={`${HOME_ROUTE}?tab=overview`} /> },
      {
        path: '/level-editor',
        lazy: async () => ({
          Component: (await import('@/features/authoring/pages/AuthoringLibraryPage')).AuthoringLibraryPage,
        }),
      },
      {
        path: '/level-editor/new/:kind',
        lazy: async () => ({
          Component: (await import('@/features/authoring/pages/ContentEditorPage')).ContentEditorPage,
        }),
      },
      {
        path: '/level-editor/chapters/new',
        lazy: async () => ({
          Component: (await import('@/features/authoring/pages/ChapterEditorPage')).ChapterEditorPage,
        }),
      },
      {
        path: '/level-editor/chapters/:chapterId',
        lazy: async () => ({
          Component: (await import('@/features/authoring/pages/ChapterEditorPage')).ChapterEditorPage,
        }),
      },
      {
        path: '/level-editor/:definitionId',
        lazy: async () => ({
          Component: (await import('@/features/authoring/pages/ContentEditorPage')).ContentEditorPage,
        }),
      },
      { path: '/store', element: <Navigate replace to={SHOP_ROUTE} /> },
      {
        path: SHOP_ROUTE,
        lazy: async () => ({
          Component: (await import('@/features/shop/pages/ShopPage')).ShopPage,
        }),
      },
      {
        path: '/settings',
        lazy: async () => ({
          Component: (await import('@/features/settings/pages/SettingsPage')).SettingsPage,
        }),
      },
    ],
  },
  // Legacy map-editor routes are kept as redirects while the old editor URLs age out.
  {
    element: (
      <Protected>
        <Outlet />
      </Protected>
    ),
    children: [
      // Editing has been removed: story maps are rendered from curriculum + story-world data.
      { path: `${LEGACY_STORY_ROUTE}/editor`, element: <Navigate replace to={storyPath()} /> },
      { path: `${LEGACY_STORY_ROUTE}/editor/official`, element: <Navigate replace to={storyPath()} /> },
      { path: `${LEGACY_STORY_ROUTE}/editor/:designId`, element: <Navigate replace to={storyPath()} /> },
      // Legacy editor route removal target: 2026-09-30.
      { path: `${LEGACY_ARCHIVE_ROUTE}/editor`, element: <LegacyStoryEditorRedirect /> },
      { path: `${LEGACY_ARCHIVE_ROUTE}/editor/:designId`, element: <LegacyStoryEditorRedirect /> },
    ],
  },
  // Staff-only admin console (its own full-screen shell; AdminLayout redirects
  // non-staff back to /home). Pages are lazy so they stay out of the app entry.
  {
    element: (
      <Protected>
        <AdminLayout />
      </Protected>
    ),
    children: [
      ...ADMIN_SECTIONS.map((section) => ({
        path: section.path,
        lazy: async () => ({ Component: await section.load() }),
      })),
      { path: '/admin/*', element: <Navigate replace to={ADMIN_ROUTES.dashboard} /> },
    ],
  },
  {
    element: (
      <Protected>
        <LevelLayout />
      </Protected>
    ),
    children: [
      { path: '/challenge-trials/:trialId', element: <ChallengeStartPage mode="start" /> },
      { path: '/challenge-trials/:trialId/replay', element: <ChallengeStartPage mode="replay" /> },
      { path: '/challenge-runs/:runId/retry', element: <ChallengeStartPage mode="retry" /> },
      {
        path: '/challenge-runs/:runId',
        lazy: async () => ({
          Component: (await import('@/features/challenges/pages/ChallengeRunPage')).ChallengeRunPage,
        }),
      },
    ],
  },
  {
    element: (
      <Protected>
        <RequireCompanion>
          <LevelLayout />
        </RequireCompanion>
      </Protected>
    ),
    children: [
      { path: '/adventure-levels/:levelId', element: <AdventureStartPage /> },
      {
        path: '/adventure-runs/:runId',
        lazy: async () => ({
          Component: (await import('@/features/adventures/pages/AdventureRunPage'))
            .AdventureRunPage,
        }),
      },
      { path: '/adventure-level-tiers/:tierId/runs', element: <TierStartPage mode="start" /> },
      { path: '/adventure-tier-runs/:runId/retry', element: <TierStartPage mode="retry" /> },
      {
        path: '/adventure-tier-runs/:runId',
        lazy: async () => ({
          Component: (await import('@/features/story-map/pages/TierRunPage'))
            .TierRunPage,
        }),
      },
    ],
  },
]

export const router = createBrowserRouter([
  {
    element: <Outlet />,
    hydrateFallbackElement: <LoadingState label="Loading application" variant="page" />,
    children: appRoutes,
  },
])
