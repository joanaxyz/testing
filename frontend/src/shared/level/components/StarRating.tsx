import { Star } from 'lucide-react'

import { cn } from '@/shared/utils/cn'

const STAR_VALUES = [1, 2, 3] as const

const SIZE_CLASS = {
  sm: 'size-3.5',
  md: 'size-5',
  lg: 'size-7',
} as const

export type StarFillState = 'empty' | 'half' | 'full'

export function StarRating({
  stars,
  fillStates,
  size = 'md',
  className,
  label = 'Stars earned',
}: {
  /** Ignored when `fillStates` is passed. */
  stars?: number
  /** Per-star fill override (index 0 = first star). When present, takes
   * priority over `stars` and supports a real half-filled visual - used by
   * the tower map node display, which maps each star to a difficulty tier
   * (easy/medium/hard) rather than a numeric grade. */
  fillStates?: StarFillState[]
  size?: keyof typeof SIZE_CLASS
  className?: string
  label?: string
}) {
  if (fillStates) {
    const earned = fillStates.filter((state) => state === 'full').length
    return (
      <span
        role="img"
        aria-label={`${label}: ${earned} of 3`}
        className={cn('inline-flex items-center gap-0.5', size === 'lg' && 'gap-1.5', className)}
      >
        {STAR_VALUES.map((value, index) => {
          const fillState = fillStates[index] ?? 'empty'
          return (
            <span key={value} className="star-rating-slot" style={{ position: 'relative' }}>
              <Star aria-hidden="true" className={cn(SIZE_CLASS[size], 'star-empty')} />
              {fillState !== 'empty' ? (
                <Star
                  aria-hidden="true"
                  className={cn(SIZE_CLASS[size], 'fill-primary text-primary')}
                  style={{
                    position: 'absolute',
                    inset: 0,
                    clipPath: fillState === 'half' ? 'inset(0 50% 0 0)' : undefined,
                  }}
                />
              ) : null}
            </span>
          )
        })}
      </span>
    )
  }

  const safeStars = Number.isFinite(stars) ? (stars as number) : 0
  const earned = Math.max(0, Math.min(3, Math.floor(safeStars)))

  return (
    <span
      role="img"
      aria-label={`${label}: ${earned} of 3`}
      className={cn('inline-flex items-center gap-0.5', size === 'lg' && 'gap-1.5', className)}
    >
      {STAR_VALUES.map((value) => (
        <Star
          key={value}
          aria-hidden="true"
          className={cn(
            SIZE_CLASS[size],
            value <= earned ? 'fill-primary text-primary' : 'star-empty',
            size === 'lg' && value <= earned && 'drop-shadow-[0_0_6px_rgba(var(--theme-primary-rgb),0.6)]',
          )}
        />
      ))}
    </span>
  )
}
