import type { CSSProperties, PointerEvent, RefObject } from 'react'

import { TierContextPanel } from '@/features/story-map/components/TierContextPanel'
import { TierDagStage } from '@/features/story-map/components/TierDagStage'
import { TierDagLegend } from '@/features/story-map/components/TierDagLegend'
import { TierContextualFeedbackPanel } from '@/features/story-map/components/TierContextualFeedbackPanel'
import { DAG_ZOOM_KEY } from '@/features/story-map/components/tierWorkspaceLayout'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import type { TierDagAnimationController } from '@/features/story-map/hooks/useTierDagAnimation'
import { LiveDagPanel } from '@/shared/level/components/LiveDagPanel'
import { ProjectStructurePanel } from '@/shared/level/components/ProjectStructurePanel'
import { ResizeHandle } from '@/shared/level/components/ResizeHandle'
import { TerminalPanel } from '@/shared/level/components/TerminalPanel'
import type { TerminalPrompt } from '@/shared/level/terminalPrompt'
import type { TerminalLine } from '@/shared/level/types'
import type {
  WorkspaceFileInput,
  WorkspaceFileRenameInput,
} from '@/shared/level/workspaceFileTypes'
import { cn } from '@/shared/utils/cn'

export type ResizeStart = (event: PointerEvent<HTMLElement>) => void

export function TierSidebar({
  run,
  projectFilesOpen,
  workspaceEditorPath,
  createDisabled,
  onToggleProjectFiles,
  onCreateFile,
  onRenameFile,
  onDeleteFile,
  onOpenFile,
}: {
  run: TierRun
  projectFilesOpen: boolean
  workspaceEditorPath: string | null
  createDisabled: boolean
  onToggleProjectFiles: () => void
  onCreateFile: (input: WorkspaceFileInput) => Promise<TierRun>
  onRenameFile: (input: WorkspaceFileRenameInput) => Promise<TierRun>
  onDeleteFile: (path: string) => Promise<TierRun>
  onOpenFile: (path: string | null) => void
}) {
  return (
    <aside
      className="gameplay-workspace__sidebar"
      style={{
        gridTemplateRows: projectFilesOpen
          ? 'minmax(13rem, 0.72fr) minmax(18rem, 0.58fr)'
          : 'minmax(13rem, 1fr) auto',
      }}
      data-testid="tier-workspace-sidebar"
      data-tour-target="level-story"
    >
      <div className="gameplay-panel-scroll app-scrollbar" data-testid="level-context-scroll">
        <TierContextPanel run={run} />
      </div>

      <div
        className={cn('gameplay-project-region', projectFilesOpen && 'is-open')}
        data-testid="project-structure-region"
        data-tour-target="project-files"
      >
        <ProjectStructurePanel
          snapshot={run.repository_state}
          rootName={run.tier.adventure_level_slug}
          className="h-full"
          selectedPath={workspaceEditorPath}
          createDisabled={createDisabled}
          isOpen={projectFilesOpen}
          onToggle={onToggleProjectFiles}
          onCreateFile={onCreateFile}
          onRenameFile={onRenameFile}
          onDeleteFile={onDeleteFile}
          onOpenFile={onOpenFile}
        />
      </div>
    </aside>
  )
}

export function TierDiagramStage({
  run,
  animation,
  hasTargetDiagram,
  diagramGridRef,
  diagramGridStyle,
  onBeginDiagramResize,
  onKeyboardDiagramResize,
  onResetDiagramResize,
}: {
  run: TierRun
  animation: TierDagAnimationController
  hasTargetDiagram: boolean
  diagramGridRef: RefObject<HTMLDivElement | null>
  diagramGridStyle: CSSProperties
  onBeginDiagramResize: ResizeStart
  onKeyboardDiagramResize: (delta: number) => void
  onResetDiagramResize: () => void
}) {
  return (
    <div
      ref={diagramGridRef}
      className={cn(
        'challenge-diagram-grid',
        hasTargetDiagram && 'has-target',
      )}
      style={diagramGridStyle}
    >
      <div className="gameplay-pane" data-tour-target="live-dag">
        <TierDagStage
          snapshot={run.repository_state}
          animation={animation}
          zoomStorageKey={DAG_ZOOM_KEY}
          className="h-full min-h-0"
        />
      </div>
      {hasTargetDiagram ? (
        <>
          <ResizeHandle
            label="Resize diagrams"
            orientation="vertical"
            className="gameplay-resize gameplay-resize--vertical"
            onPointerDown={onBeginDiagramResize}
            onKeyboardResize={onKeyboardDiagramResize}
            onReset={onResetDiagramResize}
          />
          <div className="gameplay-pane" data-tour-target="expected-state">
            <LiveDagPanel
              title="Expected State"
              snapshot={run.expected_state!}
              className="flex h-full min-h-0 flex-col"
              contentClassName="h-full min-h-0 flex-1"
              zoomStorageKey={DAG_ZOOM_KEY}
              fitViewPadding={0.16}
              layoutDirection="vertical"
            />
          </div>
        </>
      ) : null}
      <TierDagLegend />
    </div>
  )
}

export function TierTerminalStage({
  run,
  lines,
  prompt,
  terminalGridRef,
  terminalGridStyle,
  mutationPending,
  dagAnimating,
  onBeginTerminalPaneResize,
  onKeyboardTerminalPaneResize,
  onResetTerminalPaneResize,
  onCommand,
}: {
  run: TierRun
  lines: TerminalLine[]
  prompt: TerminalPrompt
  terminalGridRef: RefObject<HTMLDivElement | null>
  terminalGridStyle: CSSProperties
  mutationPending: boolean
  dagAnimating: boolean
  onBeginTerminalPaneResize: ResizeStart
  onKeyboardTerminalPaneResize: (delta: number) => void
  onResetTerminalPaneResize: () => void
  onCommand: (command: string) => void
}) {
  return (
    <div
      ref={terminalGridRef}
      data-testid="terminal-feedback-grid"
      className={cn(
        'gameplay-terminal-grid',
        run.scaffolding.contextual_feedback && 'has-feedback',
      )}
      style={terminalGridStyle}
    >
      <div className="gameplay-pane" data-tour-target="terminal">
        <TerminalPanel
          lines={lines}
          prompt={prompt}
          disabled={run.status !== 'started'}
          runDisabled={mutationPending || dagAnimating}
          processing={mutationPending}
          className="h-full"
          onCommand={onCommand}
        />
      </div>
      {run.scaffolding.contextual_feedback ? (
        <ResizeHandle
          label="Resize terminal and feedback"
          orientation="vertical"
          className="gameplay-resize gameplay-resize--vertical"
          onPointerDown={onBeginTerminalPaneResize}
          onKeyboardResize={onKeyboardTerminalPaneResize}
          onReset={onResetTerminalPaneResize}
        />
      ) : null}
      {run.scaffolding.contextual_feedback ? (
        <div className="gameplay-pane" data-tour-target="feedback">
          <TierContextualFeedbackPanel run={run} />
        </div>
      ) : null}
    </div>
  )
}
