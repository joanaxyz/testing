// Ported from archive/may30-old-modules:
// frontend/src/features/modules/orientation/visuals/CommitChainDiagram.tsx

export function CommitChainDiagram({ amended }: { amended?: boolean }) {
  return (
    <div className="grid gap-3 py-2">
      <div className="flex items-center justify-center gap-2 py-1">
        <div className="rounded-full border-2 border-muted-foreground px-3 py-2 font-mono text-xs text-muted-foreground">a1b2c3d</div>
        <span className="text-muted-foreground">{'->'}</span>
        {amended ? (
          <div className="rounded-full border-2 border-primary bg-primary/10 px-3 py-2 font-mono text-xs text-primary">f9e8d7c (new)</div>
        ) : (
          <div className="rounded-full border-2 border-dashed border-muted-foreground px-3 py-2 font-mono text-xs text-muted-foreground opacity-50">
            amended copy
          </div>
        )}
      </div>
      <p className="text-center text-xs text-muted-foreground">
        Amend writes a new commit object and repoints the branch label. The old hash does not mutate.
      </p>
    </div>
  )
}

const FIELD_EXPLANATIONS: Record<string, string> = {
  hash: 'Hash uniquely identifies a commit object. Any content or metadata change creates a different hash.',
  author: 'Author stores who originally wrote the change, used by review tools and historical blame.',
  timestamp: 'Timestamp records when the commit object was created, which helps timeline analysis.',
  message: 'Message explains intent. Good messages describe purpose and context, not just file names.',
  tree: 'Tree is the full tracked file snapshot for this commit, not only the lines edited.',
  parent: 'Parent pointer links this commit to prior history, creating the DAG structure.',
}

export function CommitAnatomyDiagram({ highlight }: { highlight: string | null }) {
  const fields = [
    { id: 'hash', label: 'Hash (SHA-1)', sample: 'a1b2c3d' },
    { id: 'author', label: 'Author', sample: 'Alex <alex@example.com>' },
    { id: 'timestamp', label: 'Timestamp', sample: '2026-05-28 10:00' },
    { id: 'message', label: 'Message', sample: 'Add login validation' },
    { id: 'tree', label: 'Tree snapshot', sample: 'files at commit time' },
    { id: 'parent', label: 'Parent pointer', sample: '-> previous commit' },
  ]
  const active = fields.find((field) => field.id === highlight)
  return (
    <div className="grid gap-3 sm:grid-cols-[1fr_16rem]">
      <div className="rounded-lg border border-border bg-black/30 p-4 font-mono text-xs leading-6">
        {fields.map((field) => (
          <div key={field.id} className={highlight === field.id ? 'text-primary' : 'text-muted-foreground'}>
            <span className="text-foreground">{field.label}:</span> {field.sample}
          </div>
        ))}
      </div>
      {active ? (
        <div className="rounded-md border border-primary/40 bg-primary/10 p-3 text-sm text-muted-foreground">
          {FIELD_EXPLANATIONS[active.id]}
        </div>
      ) : (
        <div className="rounded-md border border-border p-3 text-sm text-muted-foreground">Select a part to highlight it.</div>
      )}
    </div>
  )
}
