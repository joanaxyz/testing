// Ported from archive/may30-old-modules:
// frontend/src/features/modules/orientation/visuals/CentralizedDistributedDiagram.tsx

export function CentralizedDistributedDiagram({ active }: { active: 'centralized' | 'distributed' | null }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div
        className={`rounded-lg border p-4 transition ${active === 'centralized' ? 'border-primary bg-primary/10' : 'border-border bg-secondary/20'}`}
      >
        <div className="text-center text-xs font-semibold text-muted-foreground">Centralized model</div>
        <div className="mx-auto mt-3 flex h-16 w-24 items-center justify-center rounded-md border border-border bg-background font-mono text-xs">
          SVN server
        </div>
        <div className="mt-3 flex justify-center gap-4">
          {['Client A', 'Client B'].map((label) => (
            <div key={label} className="text-center">
              <div className="mx-auto size-8 rounded border border-dashed border-muted-foreground" />
              <div className="mt-1 text-[10px] text-muted-foreground">{label}</div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-center text-[11px] text-muted-foreground">History lives on one server. Server outage blocks most collaboration.</p>
      </div>
      <div
        className={`rounded-lg border p-4 transition ${active === 'distributed' ? 'border-primary bg-primary/10' : 'border-border bg-secondary/20'}`}
      >
        <div className="text-center text-xs font-semibold text-muted-foreground">Distributed model</div>
        <div className="flex flex-wrap justify-center gap-3">
          {['Clone 1', 'Clone 2', 'Clone 3'].map((label) => (
            <div key={label} className="text-center">
              <div className="rounded-md border border-border bg-background px-2 py-3 font-mono text-[10px]">{label}</div>
              <div className="mt-1 text-[10px] text-primary">full history</div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-center text-[11px] text-muted-foreground">Every clone has complete history. Teams can inspect history and commit locally.</p>
      </div>
    </div>
  )
}
