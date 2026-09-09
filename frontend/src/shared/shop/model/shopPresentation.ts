import { COMPANIONS } from '@/shared/cosmetics/companions/registry'
import type { ShopItem } from '@/shared/shop/api/shopApi'
import { STORY_WORLDS } from '@/shared/story-worlds/registry'
import { storyPreview } from '@/shared/story-worlds/storyPreviews'

export type ShopDisplayItem = ShopItem & {
  art?: string
  tone?: 'blue' | 'ice' | 'shadow' | 'neon'
}

function companionTone(slug: string): ShopDisplayItem['tone'] {
  if (slug === 'white') return 'ice'
  if (slug === 'black') return 'shadow'
  return 'blue'
}

export function toDisplayItem(item: ShopItem): ShopDisplayItem {
  if (item.kind === 'story') {
    const worldSlug = item.unlocks_story?.world_slug ?? item.slug
    const preview = storyPreview(worldSlug)
    return {
      ...item,
      // A story with no registered STORY_WORLDS entry has no dedicated theme
      // art yet - fall back to the neutral tone rather than hiding it (see
      // hasLocalDefinition, which used to filter these out entirely).
      art: preview?.storyMap,
      tone: STORY_WORLDS[worldSlug]?.tone ?? 'blue',
    }
  }

  const companion = COMPANIONS[item.slug]
  return {
    ...item,
    art: companion?.sprites.portrait?.src ?? companion?.sprites.idle?.src,
    tone: companionTone(item.slug),
  }
}

export function hasLocalDefinition(item: ShopItem) {
  // Stories are always shown - StoryShop already renders a graceful "no
  // preview art" empty state (see StoryContents) for a world with no
  // STORY_WORLDS entry, so there is no visually-broken case to gate here.
  // Companions still require a registered definition: their card art has no
  // placeholder path.
  if (item.kind === 'story') return true
  return Boolean(COMPANIONS[item.slug])
}

export function statusLabel(item: ShopDisplayItem): string {
  if (item.active) return 'Equipped'
  if (item.owned) return 'Owned'
  if (item.price === 0) return 'Free'
  return `${item.price.toLocaleString()} GitCoins`
}
