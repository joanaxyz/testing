import { describe, expect, it } from 'vitest'

import { aiPageContext } from './routeContext'

describe('aiPageContext', () => {
  it.each([
    ['/home', 'home'],
    ['/stories', 'stories'],
    ['/stories/arcane-spire', 'story_map'],
    ['/performance', 'performance'],
    ['/shop', 'shop'],
    ['/settings', 'settings'],
  ])('maps %s to %s', (path, context) => {
    expect(aiPageContext(path)).toBe(context)
  })

  it.each([
    '/level-editor/12',
    '/challenge-trials/4',
    '/challenge-runs/5',
    '/adventure-levels/6',
    '/adventure-runs/7',
    '/adventure-level-tiers/8/runs',
    '/adventure-tier-runs/9',
  ])('disables the assistant in workspace route %s', (path) => {
    expect(aiPageContext(path)).toBeNull()
  })
})
