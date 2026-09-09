import { Button } from '@/shared/components/Button'
import { Modal } from '@/shared/components/Modal'

export function TierExitConfirmModal({
  open,
  isExiting,
  isRetrying,
  onClose,
  onRetry,
  onExit,
}: {
  open: boolean
  isExiting: boolean
  isRetrying: boolean
  onClose: () => void
  onRetry: () => void
  onExit: () => void
}) {
  return (
    <Modal open={open} title="Exit adventure?" className="w-full max-w-md" onClose={onClose}>
      <div className="space-y-5">
        <p className="text-sm leading-6 text-muted-foreground">
          This run will be discarded. Start over with a fresh variant, or exit back to the map.
        </p>
        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" disabled={isRetrying || isExiting} onClick={onRetry}>
            {isRetrying ? 'Starting retry' : 'Retry'}
          </Button>
          <Button type="button" variant="destructive" disabled={isExiting || isRetrying} onClick={onExit}>
            {isExiting ? 'Exiting' : 'Exit'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
