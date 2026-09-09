// Ported from archive/may30-old-modules:
// frontend/src/features/modules/orientation/visuals/PlatformWorkspaceDiagram.tsx
// Import paths updated to reuse this branch's existing shared level components
// (LiveDagPanel/ProjectStructurePanel/TerminalPanel already live under
// @/shared/level/components with a compatible prop shape) instead of porting
// a second copy of them.

import { cn } from '@/shared/utils/cn'
import { LiveDagPanel } from '@/shared/level/components/LiveDagPanel'
import { ProjectStructurePanel } from '@/shared/level/components/ProjectStructurePanel'
import { TerminalPanel } from '@/shared/level/components/TerminalPanel'
import { terminalPrompt } from '@/shared/level/terminalPrompt'
import type { RepositorySnapshot, TerminalLine } from '@/shared/level/types'

const PREVIEW_PROMPT = terminalPrompt({ username: 'student', repo: 'practice' })

const HOTSPOT_EXPLANATIONS: Record<string, string> = {
  narrative: 'Read the objective and constraints before running commands.',
  files: 'Project Files mirrors the current working tree and quickly confirms file-level effects.',
  dag: 'Live DAG shows actual commit graph state after processed commands.',
  expected: 'Expected-State Diagram shows the target repository state for the current step.',
  terminal: 'Run commands here and observe output + state changes.',
  feedback: 'Contextual feedback explains consequences without revealing the exact answer path.',
  easy: 'Easy mode includes DAG, expected-state diagram, and contextual feedback.',
  medium: 'Medium mode removes direct feedback, requiring stronger state interpretation.',
  hard: 'Hard mode keeps minimal guidance so your command reasoning drives progress.',
  diagnostic: 'Diagnostic commands inspect state and do not consume action budget.',
  counted: 'Counted commands change state and consume budget.',
  retry: 'Retry variants shift details so understanding beats memorization.',
  no_answer: 'The platform does not reveal exact command sequences after failure.',
}

const PREVIEW_SNAPSHOT: RepositorySnapshot = {
  repository_initialized: true,
  commits: [],
  branches: { main: null },
  head: { type: 'branch', name: 'main' },
  staging: {},
  working_tree: {},
  conflicts: [],
}

const PREVIEW_TERMINAL_LINES: TerminalLine[] = [
  { id: 'preview-line-1', kind: 'output', text: 'Try diagnostic commands first: git status, git log --oneline --graph --all' },
]

function panelClass(activeHotspot: string | null, key: string) {
  return cn(
    'rounded-lg border border-border/70 bg-background/40 p-1 transition',
    activeHotspot === key && 'border-primary ring-2 ring-primary/60',
  )
}

export function PlatformWorkspaceDiagram({ activeHotspot }: { activeHotspot: string | null }) {
  const selectedTier = activeHotspot === 'easy' || activeHotspot === 'medium' || activeHotspot === 'hard' ? activeHotspot : 'easy'
  const showExpectedPanel = selectedTier !== 'hard'
  const showFeedbackPanel = selectedTier === 'easy'

  return (
    <div className="grid gap-3">
      <div className="rounded-lg border border-border bg-card/70 p-2">
        <div className="grid min-h-[30rem] grid-cols-[16rem_minmax(0,1fr)] gap-2 max-lg:grid-cols-1">
          <div className="grid min-h-0 grid-rows-[minmax(9rem,0.55fr)_minmax(9rem,0.45fr)] gap-2">
            <section className={panelClass(activeHotspot, 'narrative')}>
              <div className="rounded-md border border-border/70 p-2 text-xs">
                <p className="font-semibold text-foreground">SCENARIO BRIEF</p>
                <p className="mt-1 text-muted-foreground">Initialize a local repository and verify branch state.</p>
                <p className="mt-2 font-semibold text-foreground">REPOSITORY BRIEF</p>
                <ul className="mt-1 list-disc pl-4 text-muted-foreground">
                  <li>This folder is not a Git repository yet.</li>
                  <li>Default branch is main.</li>
                </ul>
              </div>
            </section>

            <section className={panelClass(activeHotspot, 'files')}>
              <ProjectStructurePanel snapshot={PREVIEW_SNAPSHOT} className="h-full min-h-0" />
            </section>
          </div>

          <div className="grid min-h-0 grid-rows-[minmax(0,1fr)_minmax(0,0.58fr)] gap-2">
            <div className={cn('grid min-h-0 gap-2', showExpectedPanel ? 'grid-cols-2' : 'grid-cols-1')}>
              <section className={panelClass(activeHotspot, 'dag')}>
                <LiveDagPanel
                  snapshot={PREVIEW_SNAPSHOT}
                  className="h-full min-h-0"
                  contentClassName="h-full"
                  fitViewPadding={0.35}
                />
              </section>
              {showExpectedPanel ? (
                <section className={panelClass(activeHotspot, 'expected')}>
                  <LiveDagPanel
                    title="Expected-State Diagram"
                    snapshot={PREVIEW_SNAPSHOT}
                    className="h-full min-h-0"
                    contentClassName="h-full"
                    fitViewPadding={0.35}
                  />
                </section>
              ) : null}
            </div>

            <div className={cn('grid min-h-0 gap-2 max-lg:grid-cols-1', showFeedbackPanel ? 'grid-cols-[minmax(0,1fr)_20rem]' : 'grid-cols-1')}>
              <section className={panelClass(activeHotspot, 'terminal')}>
                <TerminalPanel
                  lines={PREVIEW_TERMINAL_LINES}
                  prompt={PREVIEW_PROMPT}
                  disabled
                  processing={false}
                  onCommand={() => {}}
                  className="h-full min-h-0"
                />
              </section>
              {showFeedbackPanel ? (
                <section className={panelClass(activeHotspot, 'feedback')}>
                  <div className="rounded-lg border border-border bg-black/20 p-3 text-xs text-muted-foreground">
                    <p className="font-semibold text-foreground">Contextual Feedback</p>
                    <p className="mt-2">
                      After a simulator-processed command, this panel summarizes consequences without revealing the full
                      answer path.
                    </p>
                  </div>
                </section>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-secondary/20 p-4 text-sm text-muted-foreground">
        {activeHotspot ? (
          <p>
            <strong className="text-foreground">{activeHotspot.replace('_', ' ')}</strong> —{' '}
            {HOTSPOT_EXPLANATIONS[activeHotspot] ?? 'Inspect this area during practice.'}
          </p>
        ) : (
          <p>Click each label to inspect the actual practice session panels and what each one is used for.</p>
        )}
      </div>
    </div>
  )
}
