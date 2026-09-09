const STORAGE_PREFIX = 'git-it:tier-scaffold-triggers:'

export type ScaffoldTriggerFlags = {
  t1_fired: boolean
  t2_fired: boolean
  t3_fired: boolean
}

const DEFAULT_FLAGS: ScaffoldTriggerFlags = {
  t1_fired: false,
  t2_fired: false,
  t3_fired: false,
}

function storageKey(sessionId: number) {
  return `${STORAGE_PREFIX}${sessionId}`
}

export function readScaffoldTriggers(sessionId: number): ScaffoldTriggerFlags {
  if (typeof window === 'undefined') return { ...DEFAULT_FLAGS }
  try {
    const raw = window.sessionStorage.getItem(storageKey(sessionId))
    if (!raw) return { ...DEFAULT_FLAGS }
    return { ...DEFAULT_FLAGS, ...(JSON.parse(raw) as Partial<ScaffoldTriggerFlags>) }
  } catch {
    return { ...DEFAULT_FLAGS }
  }
}

export function writeScaffoldTriggers(sessionId: number, flags: ScaffoldTriggerFlags): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(storageKey(sessionId), JSON.stringify(flags))
  } catch {
    // sessionStorage may be unavailable; degrade gracefully
  }
}
