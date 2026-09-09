import { useState } from 'react'
import { toast } from 'sonner'

import { computeBudgetConsumedPct } from '@/features/challenges/scaffolding/budget'
import { evaluateScaffoldTriggers } from '@/features/challenges/scaffolding/evaluator'
import { logScaffoldTrigger } from '@/features/challenges/scaffolding/logger'
import { getScaffoldMessage } from '@/features/challenges/scaffolding/messages'
import { ScaffoldToast } from '@/features/challenges/scaffolding/ScaffoldToast'
import type { TierDifficulty, TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import { readScaffoldTriggers, writeScaffoldTriggers } from './tierScaffoldStore'
import type { ScaffoldTriggerFlags } from './tierScaffoldStore'

const SCAFFOLD_TOAST_ID = 'tier-scaffold-hint'

export function useTierScaffolding(sessionId: number) {
  const [flags, setFlags] = useState<ScaffoldTriggerFlags>(() => readScaffoldTriggers(sessionId))

  function clearToast() {
    toast.dismiss(SCAFFOLD_TOAST_ID)
  }

  function markFired(trigger: 'T1' | 'T2' | 'T3') {
    const key = `t${trigger.charAt(1).toLowerCase()}_fired` as keyof ScaffoldTriggerFlags
    const updated = { ...flags, [key]: true }
    setFlags(updated)
    writeScaffoldTriggers(sessionId, updated)
  }

  function showToast(
    trigger: 'T1' | 'T2' | 'T3',
    run: TierRun,
    onReviewMap: () => void,
  ) {
    const difficulty: TierDifficulty = run.difficulty ?? 'hard'
    const message = getScaffoldMessage(trigger, difficulty)

    toast.custom(
      () => (
        <ScaffoldToast
          message={message}
          trigger={trigger}
          difficulty={difficulty}
          onReviewMap={() => {
            clearToast()
            onReviewMap()
          }}
          onContinue={() => {
            clearToast()
            const input = document.querySelector<HTMLInputElement>('[data-command-input]')
            input?.focus()
          }}
        />
      ),
      { id: SCAFFOLD_TOAST_ID, duration: Infinity },
    )
  }

  function evaluateAndNotify(
    run: TierRun,
    stepClassification: string,
    onReviewMap: () => void,
  ) {
    if (run.status !== 'started') return
    if (stepClassification !== 'counted_action') return

    const trigger = evaluateScaffoldTriggers({
      session_complete: false,
      counted_commands_used: run.counts.counted_action_total,
      min_threshold: run.policy.min_counted_commands,
      max_limit: run.policy.max_counted_commands,
      scaffold_t1_fired: flags.t1_fired,
      scaffold_t2_fired: flags.t2_fired,
      scaffold_t3_fired: flags.t3_fired,
    })

    if (!trigger) return

    logScaffoldTrigger({
      trigger,
      difficulty: run.difficulty ?? 'hard',
      counted_commands_used: run.counts.counted_action_total,
      budget_consumed_pct: computeBudgetConsumedPct(
        run.counts.counted_action_total,
        run.policy.min_counted_commands,
        run.policy.max_counted_commands,
      ),
    })

    markFired(trigger)
    showToast(trigger, run, onReviewMap)
  }

  return { clearToast, evaluateAndNotify, flags }
}
