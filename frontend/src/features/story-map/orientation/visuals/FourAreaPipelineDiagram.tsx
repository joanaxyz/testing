// Ported from archive/may30-old-modules:
// frontend/src/features/modules/orientation/visuals/FourAreaPipelineDiagram.tsx

const STAGES = [
  { id: 'working_tree', label: 'Working tree', detail: 'Edited files not yet staged' },
  { id: 'staging', label: 'Staging', detail: 'Selected snapshot for next commit' },
  { id: 'local_repo', label: 'Local repo', detail: 'Saved commit history on your machine' },
  { id: 'remote', label: 'Remote', detail: 'Shared branch history for team sync' },
]

export function FourAreaPipelineDiagram({ activeIndex }: { activeIndex: number }) {
  return (
    <div className="rounded-lg border border-border bg-secondary/20 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {STAGES.map((stage, index) => (
          <div key={stage.id} className="flex flex-1 min-w-[4.5rem] flex-col items-center gap-2">
            <div
              className={`flex h-14 w-full items-center justify-center rounded-md border text-center text-[10px] font-medium transition ${
                index <= activeIndex ? 'border-primary bg-primary/15 text-foreground' : 'border-border text-muted-foreground'
              }`}
            >
              {index <= activeIndex ? 'FILE' : '...'}
            </div>
            <span className={index <= activeIndex ? 'text-xs font-semibold text-primary' : 'text-xs text-muted-foreground'}>
              {stage.label}
            </span>
            <span className="text-center text-[10px] text-muted-foreground">{stage.detail}</span>
            {index < STAGES.length - 1 ? <span className="hidden text-muted-foreground sm:inline">→</span> : null}
          </div>
        ))}
      </div>
    </div>
  )
}
