export type AIPageContext = 'home' | 'stories' | 'story_map' | 'performance' | 'shop' | 'settings' | 'other'

export function aiPageContext(pathname: string): AIPageContext | null {
  const excludedWorkspacePrefixes = [
    '/level-editor',
    '/challenge-trials',
    '/challenge-runs',
    '/adventure-levels',
    '/adventure-runs',
    '/adventure-level-tiers',
    '/adventure-tier-runs',
  ]
  if (excludedWorkspacePrefixes.some((prefix) => pathname.startsWith(prefix))) return null
  if (pathname === '/home' || pathname === '/') return 'home'
  if (pathname === '/stories') return 'stories'
  if (pathname.startsWith('/stories/')) return 'story_map'
  if (pathname === '/performance') return 'performance'
  if (pathname === '/shop' || pathname === '/store') return 'shop'
  if (pathname === '/settings') return 'settings'
  return 'other'
}

export function aiPageContextLabel(context: AIPageContext): string {
  return {
    home: 'Home',
    stories: 'Stories',
    story_map: 'Story map',
    performance: 'Performance',
    shop: 'Shop',
    settings: 'Settings',
    other: 'Learning page',
  }[context]
}
