import { Button } from '@/shared/components/Button'
import { cn } from '@/shared/utils/cn'

export type ScaffoldToastProps = {
  message: string
  trigger: 'T1' | 'T2' | 'T3'
  difficulty: 'easy' | 'medium' | 'hard'
  onReviewMap: () => void
  onContinue: () => void
}

const BORDER_COLOR: Record<'T1' | 'T2' | 'T3', string> = {
  T1: 'border-primary/60',
  // warning's HSL lightness (72%) is much higher than primary/destructive
  // (50%/68%), so at the same /60 alpha it composites closer to destructive
  // than to primary against this dark background - bumped to /85 so all
  // three tiers stay clearly distinguishable from each other, not just from
  // the background. See utilities.css's border-warning/85 comment.
  T2: 'border-warning/85',
  T3: 'border-destructive/60',
}

export function ScaffoldToast({
  message,
  trigger,
  onReviewMap,
  onContinue,
}: ScaffoldToastProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="scaffold-toast"
      className={cn(
        'w-[26rem] max-w-[90vw] rounded-lg border bg-background/95 p-4 shadow-xl backdrop-blur-sm',
        BORDER_COLOR[trigger],
      )}
    >
      {/* Message is plain text; no markdown or anchor rendering. */}
      <p className="whitespace-pre-line text-sm leading-6 text-foreground">{message}</p>

      <div className="mt-4 flex justify-end gap-2">
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={onContinue}
          data-testid="scaffold-continue"
        >
          Continue
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={onReviewMap}
          data-testid="scaffold-proceed"
        >
          Review map
        </Button>
      </div>
    </div>
  )
}
