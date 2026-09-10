import { useEffect, useRef, useState } from 'react'

import { isMotionReduced } from '@/shared/battle/hooks/battleMotion'

/**
 * Eased count-up from 0 to `target`, shared by game outcome stat tiles so the
 * challenge and adventure overlays keep the same timing. Jumps straight to
 * `target` when the app's motion preference is reduced, instead of running
 * the ~1s tick.
 */
export function useCountUp(target: number, duration: number, delay = 0): number {
  const [value, setValue] = useState(() => (isMotionReduced() ? target : 0))
  const frameRef = useRef<number | null>(null)

  useEffect(() => {
    if (isMotionReduced()) {
      setValue(target)
      return
    }

    const timeout = setTimeout(() => {
      const start = performance.now()
      function step(now: number) {
        const elapsed = now - start
        const progress = Math.min(elapsed / duration, 1)
        const eased = 1 - Math.pow(1 - progress, 3)
        setValue(Math.round(eased * target))
        if (progress < 1) {
          frameRef.current = requestAnimationFrame(step)
        }
      }
      frameRef.current = requestAnimationFrame(step)
    }, delay)

    return () => {
      clearTimeout(timeout)
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
    }
  }, [target, duration, delay])

  return value
}
