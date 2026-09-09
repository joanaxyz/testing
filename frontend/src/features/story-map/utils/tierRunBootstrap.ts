import type { TierRun } from '@/features/story-map/components/tierWorkspaceTypes'

const BOOTSTRAP_PREFIX = 'git-it:tier-run-bootstrap:'
const BOOTSTRAP_TTL_MS = 60_000

type BootstrapEntry = {
  run: TierRun
  storedAt: number
}

function bootstrapKey(runId: number) {
  return `${BOOTSTRAP_PREFIX}${runId}`
}

export function writeTierRunBootstrap(run: TierRun) {
  if (typeof window === 'undefined') return
  try {
    const entry: BootstrapEntry = { run, storedAt: Date.now() }
    window.sessionStorage.setItem(bootstrapKey(run.id), JSON.stringify(entry))
  } catch {
    // sessionStorage may be unavailable in private mode or quota exceeded.
  }
}

export function readTierRunBootstrap(runId: number): TierRun | undefined {
  if (typeof window === 'undefined') return undefined
  try {
    const raw = window.sessionStorage.getItem(bootstrapKey(runId))
    if (!raw) return undefined
    const entry = JSON.parse(raw) as BootstrapEntry
    if (!entry?.run || entry.run.id !== runId) {
      clearTierRunBootstrap(runId)
      return undefined
    }
    if (Date.now() - entry.storedAt > BOOTSTRAP_TTL_MS) {
      clearTierRunBootstrap(runId)
      return undefined
    }
    return entry.run
  } catch {
    clearTierRunBootstrap(runId)
    return undefined
  }
}

export function clearTierRunBootstrap(runId: number) {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(bootstrapKey(runId))
  } catch {
    // Ignore storage errors.
  }
}
