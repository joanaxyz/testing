import { Button } from '@/shared/components/Button'
import { Modal } from '@/shared/components/Modal'

export function TierStartOverConfirmModal({
  open,
  isStarting,
  onClose,
  onStartFresh,
}: {
  open: boolean
  isStarting: boolean
  onClose: () => void
  onStartFresh: () => void
}) {
  return (
    <Modal open={open} title="Start fresh attempt?" className="w-full max-w-md" onClose={onClose}>
      <div className="space-y-5">
        <p className="text-sm leading-6 text-muted-foreground">
          This starts a fresh attempt and variant. Your current workspace state resets, and the terminal history from this attempt will not carry over.
        </p>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>Completed progress is not deleted.</li>
          <li>This action cannot be undone.</li>
        </ul>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" disabled={isStarting} onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" disabled={isStarting} onClick={onStartFresh}>
            {isStarting ? 'Starting' : 'Start fresh attempt'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
