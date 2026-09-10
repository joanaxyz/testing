import { renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { useCountUp } from './useCountUp'

describe('useCountUp', () => {
  afterEach(() => {
    delete document.documentElement.dataset.motion
  })

  it('jumps straight to the target when motion is reduced, instead of ticking', () => {
    document.documentElement.dataset.motion = 'reduced'

    const { result } = renderHook(() => useCountUp(42, 900, 160))

    expect(result.current).toBe(42)
  })

  it('starts from 0 and only reaches the target after ticking when motion is full', () => {
    document.documentElement.dataset.motion = 'full'

    const { result } = renderHook(() => useCountUp(42, 900, 0))

    expect(result.current).toBe(0)
  })
})
