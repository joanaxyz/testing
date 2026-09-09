import type { CSSProperties, RefObject } from 'react'

import {
  TierDiagramStage,
  TierSidebar,
  TierTerminalStage,
  type ResizeStart,
} from '@/features/story-map/components/TierWorkspacePanels'
import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'
import { ResizeHandle } from '@/shared/level/components/ResizeHandle'
import { WorkspaceEditorOverlay } from '@/shared/level/components/WorkspaceEditorOverlay'
import type { TerminalPrompt } from '@/shared/level/terminalPrompt'
import type { TerminalLine } from '@/shared/level/types'
import type {
  WorkspaceFileInput,
  WorkspaceFileRenameInput,
} from '@/shared/level/workspaceFileTypes'
import type { TierDagAnimationController } from '@/features/story-map/hooks/useTierDagAnimation'

export function TierWorkspaceMain({
  run,
  lines,
  shellPrompt,
  projectFilesOpen,
  workspaceEditorPath,
  createDisabled,
  writeDisabled,
  workspaceGridRef,
  workspaceGridStyle,
  dagAnimation,
  hasTargetDiagram,
  diagramGridRef,
  diagramGridStyle,
  terminalGridRef,
  terminalGridStyle,
  mutationPending,
  onToggleProjectFiles,
  onCreateFile,
  onRenameFile,
  onDeleteFile,
  onOpenFile,
  onBeginDiagramResize,
  onBeginTerminalResize,
  onBeginTerminalPaneResize,
  onKeyboardDiagramResize,
  onKeyboardTerminalResize,
  onKeyboardTerminalPaneResize,
  onResetDiagramResize,
  onResetTerminalResize,
  onResetTerminalPaneResize,
  onCommand,
  onCloseEditor,
  onWriteFile,
}: {
  run: TierRun
  lines: TerminalLine[]
  shellPrompt: TerminalPrompt
  projectFilesOpen: boolean
  workspaceEditorPath: string | null
  createDisabled: boolean
  writeDisabled: boolean
  workspaceGridRef: RefObject<HTMLElement | null>
  workspaceGridStyle: CSSProperties
  dagAnimation: TierDagAnimationController
  hasTargetDiagram: boolean
  diagramGridRef: RefObject<HTMLDivElement | null>
  diagramGridStyle: CSSProperties
  terminalGridRef: RefObject<HTMLDivElement | null>
  terminalGridStyle: CSSProperties
  mutationPending: boolean
  onToggleProjectFiles: () => void
  onCreateFile: (input: WorkspaceFileInput) => Promise<TierRun>
  onRenameFile: (input: WorkspaceFileRenameInput) => Promise<TierRun>
  onDeleteFile: (path: string) => Promise<TierRun>
  onOpenFile: (path: string | null) => void
  onBeginDiagramResize: ResizeStart
  onBeginTerminalResize: ResizeStart
  onBeginTerminalPaneResize: ResizeStart
  onKeyboardDiagramResize: (delta: number) => void
  onKeyboardTerminalResize: (delta: number) => void
  onKeyboardTerminalPaneResize: (delta: number) => void
  onResetDiagramResize: () => void
  onResetTerminalResize: () => void
  onResetTerminalPaneResize: () => void
  onCommand: (command: string) => void
  onCloseEditor: () => void
  onWriteFile: (input: WorkspaceFileInput) => Promise<TierRun>
}) {
  return (
    <main className="gameplay-workspace">
      <TierSidebar
        run={run}
        projectFilesOpen={projectFilesOpen}
        workspaceEditorPath={workspaceEditorPath}
        createDisabled={createDisabled}
        onToggleProjectFiles={onToggleProjectFiles}
        onCreateFile={onCreateFile}
        onRenameFile={onRenameFile}
        onDeleteFile={onDeleteFile}
        onOpenFile={onOpenFile}
      />
      <section
        ref={workspaceGridRef}
        className="gameplay-workspace__main challenge-workspace__main"
        style={workspaceGridStyle}
      >
        <TierDiagramStage
          run={run}
          animation={dagAnimation}
          hasTargetDiagram={hasTargetDiagram}
          diagramGridRef={diagramGridRef}
          diagramGridStyle={diagramGridStyle}
          onBeginDiagramResize={onBeginDiagramResize}
          onKeyboardDiagramResize={onKeyboardDiagramResize}
          onResetDiagramResize={onResetDiagramResize}
        />
        <ResizeHandle
          label="Resize terminal height"
          orientation="horizontal"
          className="gameplay-resize gameplay-resize--horizontal"
          onPointerDown={onBeginTerminalResize}
          onKeyboardResize={onKeyboardTerminalResize}
          onReset={onResetTerminalResize}
        />
        <TierTerminalStage
          run={run}
          lines={lines}
          prompt={shellPrompt}
          terminalGridRef={terminalGridRef}
          terminalGridStyle={terminalGridStyle}
          mutationPending={mutationPending}
          dagAnimating={dagAnimation.animating}
          onBeginTerminalPaneResize={onBeginTerminalPaneResize}
          onKeyboardTerminalPaneResize={onKeyboardTerminalPaneResize}
          onResetTerminalPaneResize={onResetTerminalPaneResize}
          onCommand={onCommand}
        />
      </section>
      <WorkspaceEditorOverlay
        snapshot={run.repository_state}
        filePath={workspaceEditorPath}
        open={Boolean(workspaceEditorPath)}
        writeDisabled={writeDisabled}
        onClose={onCloseEditor}
        onWriteFile={onWriteFile}
      />
    </main>
  )
}
