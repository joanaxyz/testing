import { CircleCheckBig, Info, TriangleAlert } from 'lucide-react'
import type { ComponentType } from 'react'

import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import { TIER_RESULT_TARGET_MATCHED } from '@/features/story-map/components/tierWorkspaceTypes'
import { isEphemeralStep } from '@/shared/level/terminalSteps'
import { Card, CardContent, CardHeader } from '@/shared/components/Card'

type NodeTone = { icon: ComponentType<{ className?: string }>; tone: '' | 'feedback-node--success' | 'feedback-node--warning' }

function toneForStep(resultCategory: string): NodeTone {
  if (resultCategory === TIER_RESULT_TARGET_MATCHED) return { icon: CircleCheckBig, tone: 'feedback-node--success' }
  if (resultCategory.includes('error') || resultCategory.includes('rejected'))
    return { icon: TriangleAlert, tone: 'feedback-node--warning' }
  return { icon: Info, tone: '' }
}

function timeLabel(createdAt: string) {
  const date = new Date(createdAt)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString([], { hour12: false })
}

/** Mirrors ContextualFeedbackPanel: one node per counted turn, newest first. */
export function TierContextualFeedbackPanel({ run }: { run: TierRun }) {
  if (!run.scaffolding.contextual_feedback) return null

  const steps = (run.steps ?? []).filter((step) => !isEphemeralStep(step) && step.contextual_feedback)
  const entries = steps
    .map((step, index) => ({
      id: step.id,
      turn: index + 1,
      time: timeLabel(step.created_at),
      command: step.command_text,
      text: step.contextual_feedback,
      ...toneForStep(step.result_category),
    }))
    .reverse()

  return (
    <Card className="h-full w-full min-w-0 shadow-none lvlctx flex min-h-0 flex-col">
      <CardHeader className="lvlctx-header">
        <span className="panel-eyebrow">Contextual Feedback</span>
      </CardHeader>
      <CardContent className="lvlctx-body feedback-scroll app-scrollbar">
        <div aria-live="polite">
          {entries.length === 0 ? (
            <p className="feedback-text--empty">Run a command to see its consequence here.</p>
          ) : (
            <ol className="feedback-history">
              {entries.map((entry) => (
                <li className="feedback-entry" key={entry.id}>
                  <span className={`feedback-node ${entry.tone}`} aria-hidden="true">
                    <entry.icon />
                  </span>
                  <div className="feedback-card">
                    <span className="feedback-turn">
                      Turn {entry.turn}
                      {entry.time ? `  ${entry.time}` : ''}
                    </span>
                    <span className="feedback-command">{entry.command}</span>
                    <p className="feedback-text">{entry.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
