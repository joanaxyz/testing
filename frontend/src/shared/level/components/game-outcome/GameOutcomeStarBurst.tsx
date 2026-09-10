import type { CSSProperties } from 'react'

// Fractional (x%, y%) position of each star within the baked win-N star-arc
// art (left, top, right), used to land an impact burst under it. The art is
// a single raster sheet with 1-3 stars already filled in, so this is the
// lightest way to give each earned star its own "landing" moment without
// re-authoring the art as separate layers.
const STAR_POSITIONS: Array<{ x: number; y: number }> = [
  { x: 20, y: 48 },
  { x: 50, y: 31 },
  { x: 80, y: 48 },
]

const SPARK_COUNT = 6

/**
 * Staggered glow + spark burst under each earned star, timed to land one at
 * a time after the star art pops in. Reuses the confetti layer's CSS
 * custom-property particle technique rather than a new particle system.
 * Caller is responsible for not rendering this when motion is reduced.
 */
export function GameOutcomeStarBurst({ earnedStars, startDelayMs, stepMs }: { earnedStars: number; startDelayMs: number; stepMs: number }) {
  const bursts = STAR_POSITIONS.slice(0, Math.max(0, Math.min(3, earnedStars)))

  return (
    <div className="game-outcome-star-burst-layer pointer-events-none absolute inset-0" aria-hidden="true">
      {bursts.map((position, index) => {
        const delay = startDelayMs + index * stepMs
        const style = {
          '--burst-x': `${position.x}%`,
          '--burst-y': `${position.y}%`,
          '--burst-delay': `${delay}ms`,
        } as CSSProperties

        return (
          <span className="game-outcome-star-burst" key={`${position.x}-${position.y}`} style={style}>
            <span className="game-outcome-star-burst-ring" />
            {Array.from({ length: SPARK_COUNT }, (_, sparkIndex) => {
              const angle = (360 / SPARK_COUNT) * sparkIndex
              const sparkStyle = {
                '--spark-angle': `${angle}deg`,
                '--spark-delay': `${delay + 30}ms`,
              } as CSSProperties
              return <span className="game-outcome-star-spark" key={angle} style={sparkStyle} />
            })}
          </span>
        )
      })}
    </div>
  )
}
