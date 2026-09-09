import { isLegacyStoryRoute } from './legacyRoutes'

const DEFAULT_STORY_SLUG = 'git-it-legacy'

export const HOME_ROUTE = '/home'
export const SHOP_ROUTE = '/shop'
export const PERFORMANCE_ROUTE = '/performance'
export const STORIES_ROUTE = '/stories'
export const STORY_DETAIL_ROUTE = `${STORIES_ROUTE}/:storySlug`
export const DESIGN_PREVIEW_STORY_MAP_ROUTE = '/design-preview/story-map'
export const ADMIN_ROUTES = {
  dashboard: '/admin',
  users: '/admin/users',
  economy: '/admin/economy',
  curriculum: '/admin/curriculum',
  content: '/admin/content',
  analytics: '/admin/analytics',
  moderation: '/admin/moderation',
  settings: '/admin/settings',
} as const

export function storyPath(slug: string = DEFAULT_STORY_SLUG): string {
  return `${STORIES_ROUTE}/${slug}`
}

export function storyPathWithQuery(slug: string = DEFAULT_STORY_SLUG, query: string): string {
  const suffix = query.startsWith('?') ? query : `?${query}`
  return `${storyPath(slug)}${suffix}`
}


export function isStoryMapRoute(pathname: string): boolean {
  if (pathname.includes('/editor')) return false
  return pathname.startsWith(STORIES_ROUTE) || isLegacyStoryRoute(pathname)
}
