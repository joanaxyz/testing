// Ported from archive/may30-old-modules:
// frontend/src/features/modules/orientation/OrientationStepView.tsx
//
// Read-only step-through: the 10 local-state-only step kinds (continue,
// compare_toggle, match_reveal, pipeline, status_annotate, anatomy,
// immutability_demo, dag_explore, command_builder, error_parse,
// platform_panel) are ported unchanged - none of them ever called a backend
// endpoint in the old app either. `git_command`/`shell_command` (the two
// kinds that drove a live simulated terminal via a session API) are replaced
// with a static instructional card per the approved read-only design - no
// TerminalPanel, no session, no command validation.

import { useMemo, useState } from 'react'

import { LiveDagPanel } from '@/shared/level/components/LiveDagPanel'
import type { OrientationStep } from '@/features/story-map/orientation/types'
import { normalizeBuilderCommand } from '@/features/story-map/orientation/types'
import { CentralizedDistributedDiagram } from '@/features/story-map/orientation/visuals/CentralizedDistributedDiagram'
import { CommitAnatomyDiagram, CommitChainDiagram } from '@/features/story-map/orientation/visuals/CommitChainDiagram'
import { FourAreaPipelineDiagram } from '@/features/story-map/orientation/visuals/FourAreaPipelineDiagram'
import { PlatformWorkspaceDiagram } from '@/features/story-map/orientation/visuals/PlatformWorkspaceDiagram'
import { Button } from '@/shared/components/Button'
import { cn } from '@/shared/utils/cn'

export function OrientationStepView({
  step,
  layout,
  onStepComplete,
  hasNextStep,
  onContinueToNext,
}: {
  step: OrientationStep
  layout: string
  onStepComplete: () => void
  hasNextStep: boolean
  onContinueToNext: () => void
}) {
  const [done, setDone] = useState(false)
  const [pipelineStage, setPipelineStage] = useState(0)
  const [selectedCompare, setSelectedCompare] = useState<string | null>(null)
  const [matchSelections, setMatchSelections] = useState<Record<string, string>>({})
  const [matchRevealed, setMatchRevealed] = useState(false)
  const [anatomyPart, setAnatomyPart] = useState<string | null>(null)
  const [immutabilityToggled, setImmutabilityToggled] = useState(false)
  const [builderParts, setBuilderParts] = useState<string[]>([])
  const [visitedHotspots, setVisitedHotspots] = useState<Set<string>>(new Set())
  const [activeHotspot, setActiveHotspot] = useState<string | null>(null)
  const [errorHint, setErrorHint] = useState<string | null>(null)

  const complete = () => {
    setDone(true)
    onStepComplete()
  }
  const proceed = () => {
    complete()
    if (hasNextStep) onContinueToNext()
  }

  const builderTarget = normalizeBuilderCommand(step.target ?? '')
  const builderBuilt = useMemo(() => normalizeBuilderCommand(builderParts.join(' ')), [builderParts])
  const allPairsSelected =
    (step.pairs ?? []).length > 0 &&
    (step.pairs ?? []).every((pair) => Boolean(matchSelections[pair.scenario]?.trim()))

  const content = (() => {
    switch (step.kind) {
      case 'continue':
        return (
          <div className="grid gap-4">
            {step.body ? <p className="text-sm leading-7 text-muted-foreground">{step.body}</p> : null}
            <Button type="button" onClick={proceed}>
              Continue
            </Button>
          </div>
        )
      case 'compare_toggle':
        return (
          <div className="grid gap-4">
            <CentralizedDistributedDiagram
              active={selectedCompare === 'centralized' ? 'centralized' : selectedCompare === 'distributed' ? 'distributed' : null}
            />
            <div className="grid gap-3 sm:grid-cols-2">
              {(step.options ?? []).map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={cn(
                    'rounded-lg border p-4 text-left transition',
                    selectedCompare === option.id ? 'border-primary bg-primary/10' : 'border-border bg-secondary/30',
                  )}
                  onClick={() => setSelectedCompare(option.id)}
                >
                  <div className="font-semibold">{option.label}</div>
                  {selectedCompare === option.id ? (
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{option.detail}</p>
                  ) : null}
                </button>
              ))}
              <Button type="button" className="sm:col-span-2" disabled={!selectedCompare} onClick={proceed}>
                Continue
              </Button>
            </div>
          </div>
        )
      case 'match_reveal':
        return (
          <div className="grid gap-3">
            {(step.pairs ?? []).map((pair) => (
              <div key={pair.scenario} className="flex flex-wrap items-center gap-2 rounded-md border border-border p-3">
                <span className="flex-1 text-sm">{pair.scenario}</span>
                <select
                  className="rounded border border-border bg-background px-2 py-1 text-sm"
                  value={matchSelections[pair.scenario] ?? ''}
                  onChange={(event) =>
                    setMatchSelections((current) => ({ ...current, [pair.scenario]: event.target.value }))
                  }
                >
                  <option value="">Choose…</option>
                  <option value="history">History</option>
                  <option value="collaboration">Collaboration</option>
                  <option value="recovery">Recovery</option>
                </select>
              </div>
            ))}
            <Button type="button" variant="outline" onClick={() => setMatchRevealed(true)} disabled={!allPairsSelected}>
              Reveal answers
            </Button>
            {matchRevealed ? (
              <div className="text-sm text-muted-foreground">
                {(step.pairs ?? []).map((pair) => (
                  <div key={pair.scenario}>
                    {pair.scenario} → <strong>{pair.problem}</strong>
                  </div>
                ))}
                <Button type="button" className="mt-3" onClick={proceed}>
                  Continue
                </Button>
              </div>
            ) : null}
          </div>
        )
      case 'git_command':
      case 'shell_command':
        return (
          <div className="grid gap-3">
            <div className="rounded-lg border border-border bg-secondary/20 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {step.kind === 'git_command' ? 'Command' : 'Shell command'}
              </p>
              <pre className="mt-2 overflow-auto rounded-md border border-border bg-black/40 p-3 font-mono text-sm text-foreground">
                {(step.accept_prefixes ?? [])[0] ?? step.hint ?? 'See the prompt above.'}
              </pre>
              {step.success_output ? (
                <>
                  <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Expected output</p>
                  <pre className="mt-2 overflow-auto rounded-md border border-border bg-black/40 p-3 font-mono text-xs text-muted-foreground">
                    {step.success_output}
                  </pre>
                </>
              ) : null}
              {step.hint ? <p className="mt-3 text-sm text-muted-foreground">{step.hint}</p> : null}
            </div>
            <Button type="button" onClick={proceed}>
              Continue
            </Button>
          </div>
        )
      case 'pipeline':
        return (
          <div className="grid gap-4">
            <FourAreaPipelineDiagram activeIndex={pipelineStage} />
            <Button
              type="button"
              onClick={() => {
                if (pipelineStage + 1 >= (step.stages?.length ?? 0)) complete()
                else setPipelineStage((value) => value + 1)
              }}
            >
              {pipelineStage + 1 >= (step.stages?.length ?? 0) ? 'Finish pipeline' : 'Move file to next area'}
            </Button>
          </div>
        )
      case 'status_annotate':
        return (
          <div className="grid gap-3">
            <pre className="overflow-auto rounded-lg border border-border bg-black/40 p-4 font-mono text-xs leading-6 text-muted-foreground">
              {step.sample_output}
            </pre>
            <Button type="button" onClick={proceed}>
              Continue
            </Button>
          </div>
        )
      case 'anatomy':
        return (
          <div className="grid gap-4">
            <CommitAnatomyDiagram highlight={anatomyPart} />
            <div className="flex flex-wrap gap-2">
              {(step.parts ?? []).map((part) => (
                <button
                  key={part}
                  type="button"
                  className={cn(
                    'rounded-md border px-3 py-1.5 text-sm capitalize',
                    anatomyPart === part ? 'border-primary bg-primary/10' : 'border-border',
                  )}
                  onClick={() => setAnatomyPart(part)}
                >
                  {part}
                </button>
              ))}
            </div>
            <Button type="button" disabled={!anatomyPart} onClick={proceed}>
              Continue
            </Button>
          </div>
        )
      case 'immutability_demo':
        return (
          <div className="grid gap-3">
            <p className="text-sm text-muted-foreground">
              Amending creates a <strong>new</strong> commit; the original stays in history unchanged.
            </p>
            <CommitChainDiagram amended={immutabilityToggled} />
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setImmutabilityToggled(true)
                complete()
              }}
            >
              Simulate amend and update commit hash
            </Button>
          </div>
        )
      case 'dag_explore':
        return (
          <div className="grid gap-3">
            {step.initial_state ? (
              <LiveDagPanel snapshot={step.initial_state} title="Commit graph" className="min-h-[220px]" />
            ) : null}
            <p className="text-sm text-muted-foreground">
              Find branch labels <strong>main</strong> and <strong>feature</strong>, and note where HEAD points.
            </p>
            <Button type="button" onClick={proceed}>
              Continue
            </Button>
          </div>
        )
      case 'command_builder':
        return (
          <div className="grid gap-3">
            <div className="flex flex-wrap gap-2">
              {['git', 'commit', 'log', 'status', '-m', '--oneline', '--graph', '--all', '"message"'].map((token) => (
                <Button
                  key={token}
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => setBuilderParts((current) => [...current, token])}
                >
                  {token}
                </Button>
              ))}
              <Button type="button" size="sm" variant="ghost" onClick={() => setBuilderParts([])}>
                Clear
              </Button>
            </div>
            <pre className="rounded-md border border-border bg-black/40 p-3 font-mono text-sm">{builderBuilt || '…'}</pre>
            <Button type="button" disabled={!builderTarget || builderBuilt !== builderTarget} onClick={proceed}>
              Continue
            </Button>
          </div>
        )
      case 'error_parse':
        return (
          <div className="grid gap-3">
            <pre className="rounded-md border border-border bg-black/40 p-3 font-mono text-xs text-warning">
              {step.error_text}
            </pre>
            {errorHint ? <p className="text-sm text-accent">{errorHint}</p> : null}
            <div className="flex flex-wrap gap-2">
              {['subcommand', 'flag', 'repository', 'argument'].map((choice) => (
                <Button
                  key={choice}
                  type="button"
                  variant="outline"
                  onClick={() => {
                    if (choice === step.answer) proceed()
                    else setErrorHint('Read which part of the command context failed.')
                  }}
                >
                  {choice}
                </Button>
              ))}
            </div>
          </div>
        )
      case 'platform_panel':
        return (
          <div className="grid gap-3">
            <PlatformWorkspaceDiagram activeHotspot={activeHotspot} />
            {step.body ? <p className="text-sm leading-7 text-muted-foreground">{step.body}</p> : null}
            <div className="flex flex-wrap gap-2">
              {(step.hotspots ?? []).map((spot) => (
                <Button
                  key={spot}
                  type="button"
                  size="sm"
                  variant={activeHotspot === spot ? 'default' : 'outline'}
                  onClick={() => {
                    setActiveHotspot(spot)
                    setVisitedHotspots((current) => new Set([...current, spot]))
                  }}
                >
                  {spot.replace('_', ' ')}
                </Button>
              ))}
            </div>
            <Button type="button" disabled={visitedHotspots.size < (step.hotspots?.length ?? 0)} onClick={proceed}>
              Continue
            </Button>
          </div>
        )
      default:
        return (
          <Button type="button" onClick={proceed}>
            Continue
          </Button>
        )
    }
  })()

  return (
    <div
      className={cn(
        'grid gap-4',
        layout === 'guide_terminal' && step.kind === 'continue' && 'lg:col-span-1',
      )}
    >
      <div>
        <h3 className="text-lg font-bold">{step.title}</h3>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">{step.prompt}</p>
      </div>
      {content}
      {done ? <p className="text-sm text-primary">Step completed.</p> : null}
    </div>
  )
}
