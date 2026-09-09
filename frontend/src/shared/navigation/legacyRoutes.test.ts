import { describe, expect, it } from 'vitest'

import {
  LEGACY_ARCHIVE_ROUTE,
  LEGACY_DESIGN_PREVIEW_STORY_ROUTE,
  LEGACY_MY_STORY_ROUTE,
  LEGACY_STORY_ROUTE,
  LEGACY_STORIES_ROUTE,
  isLegacyStoryRoute,
} from './legacyRoutes'
import { DESIGN_PREVIEW_STORY_MAP_ROUTE, STORIES_ROUTE, isStoryMapRoute, storyPath } from './routes'

describe('legacy route compatibility', () => {
  it('keeps deprecated paths isolated while canonical routes use current vocabulary', () => {
    expect(storyPath()).toBe('/stories/git-it-legacy')
    expect(STORIES_ROUTE).toBe('/stories')
    expect(DESIGN_PREVIEW_STORY_MAP_ROUTE).toBe('/design-preview/story-map')

    expect(LEGACY_STORY_ROUTE).toBe('/tower')
    expect(LEGACY_STORIES_ROUTE).toBe('/towers')
    expect(LEGACY_ARCHIVE_ROUTE).toBe('/archive')
    expect(LEGACY_MY_STORY_ROUTE).toBe('/my-tower')
    expect(LEGACY_DESIGN_PREVIEW_STORY_ROUTE).toBe('/design-preview/tower')
  })

  it('recognizes only compatibility routes as legacy story-map routes', () => {
    expect(isLegacyStoryRoute('/tower')).toBe(true)
    expect(isLegacyStoryRoute('/towers/arcane-spire')).toBe(true)
    expect(isLegacyStoryRoute('/archive/shared/1')).toBe(true)
    expect(isLegacyStoryRoute('/my-tower')).toBe(true)

    expect(isLegacyStoryRoute('/stories')).toBe(false)
    expect(isLegacyStoryRoute('/stories/arcane-spire')).toBe(false)
    expect(isLegacyStoryRoute('/shop')).toBe(false)
  })

  it('keeps canonical and legacy map-route detection behavior explicit', () => {
    expect(isStoryMapRoute('/stories')).toBe(true)
    expect(isStoryMapRoute('/stories/arcane-spire')).toBe(true)
    expect(isStoryMapRoute('/tower')).toBe(true)
    expect(isStoryMapRoute('/tower/editor')).toBe(false)
    expect(isStoryMapRoute('/shop')).toBe(false)
  })
})
