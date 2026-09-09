import type { TierDagAnimationController } from '@/features/story-map/hooks/useTierDagAnimation'
import { LiveDagPanel } from '@/shared/level/components/LiveDagPanel'
import type { RepositorySnapshot } from '@/shared/level/types'
import { cn } from '@/shared/utils/cn'

export function TierDagStage({
  snapshot,
  animation,
  zoomStorageKey,
  className,
}: {
  snapshot: RepositorySnapshot
  animation: TierDagAnimationController
  zoomStorageKey: string
  className?: string
}) {
  return (
    <section
      className={cn('challenge-dag-stage', `is-${animation.activity}`, className)}
      data-dag-activity={animation.activity}
      data-testid="tier-dag-stage"
      aria-label="Repository puzzle stage"
    >
      <LiveDagPanel
        title="Live DAG"
        snapshot={snapshot}
        className="flex h-full min-h-0 flex-col"
        contentClassName="h-full min-h-0 flex-1"
        zoomStorageKey={zoomStorageKey}
        fitViewPadding={0.16}
        animateChanges
        pauseChangeAnimations={animation.activity === 'processing'}
        activity={animation.activity}
        layoutDirection="vertical"
      />
    </section>
  )
}
