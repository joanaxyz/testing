import type { CSSProperties, ComponentType } from 'react'

import { useCountUp } from './useCountUp'

export type GameOutcomeStatTileProps = {
  label: string
  numerator: number
  denominator?: number
  suffix?: string
  helper: string
  accentColor: string
  animationDelay: number
  /** Optional glyph rendered in the accent chip; lucide icons satisfy this. */
  icon?: ComponentType<{ className?: string }>
  /** Neon icon art (battle-outcome assets); wins over `icon` when set. */
  iconSrc?: string
}

/**
 * Animated stat tile shared by the challenge and adventure game outcome modals.
 */
export function GameOutcomeStatTile({
  label,
  numerator,
  denominator,
  suffix = '',
  helper,
  accentColor,
  animationDelay,
  icon: Icon,
  iconSrc,
}: GameOutcomeStatTileProps) {
  const animatedNum = useCountUp(numerator, 900, animationDelay + 50)
  const hasBar = denominator !== undefined && denominator > 0
  const fillPercent = hasBar ? Math.min(100, Math.round((numerator / denominator) * 100)) : 0

  return (
    <div
      className="game-outcome-stat-tile group relative overflow-hidden rounded-xl border border-border/60 transition-all duration-200 hover:-translate-y-0.5"
      style={
        {
          animationDelay: `${animationDelay}ms`,
          background: `linear-gradient(150deg, color-mix(in srgb, ${accentColor} 16%, transparent) 0%, color-mix(in srgb, ${accentColor} 5%, transparent) 52%, hsl(var(--background) / 0.34) 100%)`,
          boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${accentColor} 28%, transparent)`,
        } as CSSProperties
      }
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -right-5 -top-6 size-16 rounded-full opacity-30 blur-2xl transition-opacity duration-200 group-hover:opacity-55"
        style={{ background: accentColor }}
      />

      <div className="game-outcome-stat-tile-row relative">
        {iconSrc ? (
          <img className="game-outcome-stat-icon" src={iconSrc} alt="" aria-hidden="true" />
        ) : Icon ? (
          <span
            className="game-outcome-stat-chip"
            style={{ color: accentColor, background: `color-mix(in srgb, ${accentColor} 18%, transparent)` }}
          >
            <Icon className="size-3.5" />
          </span>
        ) : null}

        <div className="game-outcome-stat-body">
          <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{label}</span>

          <div className="flex items-baseline gap-1">
            <span
              className="font-mono text-xl font-extrabold tracking-tight tabular-nums"
              style={{ color: accentColor }}
            >
              {animatedNum}
              {suffix}
            </span>
            {denominator !== undefined ? (
              <span className="text-sm font-semibold text-muted-foreground">/ {denominator}</span>
            ) : null}
          </div>

          {hasBar ? (
            <div className="relative mt-1 h-1.5 overflow-hidden rounded-full bg-border/40">
              <div
                className="h-full rounded-full transition-[width] duration-700 ease-out"
                style={{
                  width: `${fillPercent}%`,
                  background: accentColor,
                  boxShadow: `0 0 10px color-mix(in srgb, ${accentColor} 70%, transparent)`,
                }}
              />
            </div>
          ) : null}

          <div className="mt-1 text-xs leading-snug text-muted-foreground">{helper}</div>
        </div>
      </div>
    </div>
  )
}
