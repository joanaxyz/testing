import { useCallback, useEffect, useRef, useState } from 'react'

import type { CommandSubmissionOutcome } from '@/shared/level-runtime/commandOutcome'
import type { DagActivity } from '@/shared/level/components/live-dag/types'

export type TierDagAnimationController = {
  activity: DagActivity
  animating: boolean
  onCommandStart: () => void
  onCommandResolved: (outcome: CommandSubmissionOutcome) => void
  onCommandError: () => void
}

/**
 * Adventure-tier repository choreography, mirroring useChallengeDagAnimation.
 * Optimistic Git updates render while the graph is in `processing`, then
 * their node/edge/ref deltas are released together when the server accepts
 * the command.
 */
export function useTierDagAnimation(): TierDagAnimationController {
  const sequenceRef = useRef(0)
  const settleTimerRef = useRef<number | null>(null)
  const [activity, setActivity] = useState<DagActivity>('idle')
  const [animating, setAnimating] = useState(false)

  const clearSettleTimer = useCallback(() => {
    if (settleTimerRef.current === null) return
    window.clearTimeout(settleTimerRef.current)
    settleTimerRef.current = null
  }, [])

  useEffect(() => clearSettleTimer, [clearSettleTimer])

  const settle = useCallback((sequence: number, delay: number) => {
    clearSettleTimer()
    settleTimerRef.current = window.setTimeout(() => {
      settleTimerRef.current = null
      if (sequenceRef.current !== sequence) return
      setActivity('idle')
      setAnimating(false)
    }, delay)
  }, [clearSettleTimer])

  const onCommandStart = useCallback(() => {
    clearSettleTimer()
    sequenceRef.current += 1
    setActivity('processing')
    setAnimating(true)
  }, [clearSettleTimer])

  const onCommandResolved = useCallback((outcome: CommandSubmissionOutcome) => {
    const sequence = sequenceRef.current
    const resultActivity = activityForOutcome(outcome)
    setActivity(resultActivity)
    settle(sequence, outcome.solved ? 1000 : resultActivity === 'updated' ? 900 : 520)
  }, [settle])

  const onCommandError = useCallback(() => {
    clearSettleTimer()
    sequenceRef.current += 1
    const sequence = sequenceRef.current
    setActivity('error')
    setAnimating(true)
    settle(sequence, 520)
  }, [clearSettleTimer, settle])

  return {
    activity,
    animating,
    onCommandStart,
    onCommandResolved,
    onCommandError,
  }
}

function activityForOutcome(outcome: CommandSubmissionOutcome): DagActivity {
  if (outcome.solved) return 'solved'
  if (!outcome.processed) return 'error'
  if (outcome.rules_delta > 0) return 'updated'
  return 'unchanged'
}
