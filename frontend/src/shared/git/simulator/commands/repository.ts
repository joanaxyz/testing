import type { RepositoryValue } from '@/shared/level/types'
import { hasOption, optionValues } from '@/shared/git/simulator/parser'
import { applyRemoteFixtureBranches, commitById, headBranch, isRecord, materializeRemoteCommits, setOperationMetadata } from '@/shared/git/simulator/state'
import { configGet } from '@/shared/git/simulator/commands/scenarioDiagnostics'
import { SimulatorCommandError, type CommandOutcome, type MutableRepositoryState, type ParsedGitCommand } from '@/shared/git/simulator/types'

export function gitInit(state: MutableRepositoryState, parsed: ParsedGitCommand): CommandOutcome {
  const reinitialized = Boolean(state.repository_initialized)
  const branchValues = optionValues(parsed, '-b', '--initial-branch')
  const branch = String(branchValues.at(-1) ?? headBranch(state) ?? 'main')
  const directory = parsed.args[0] ?? null
  const quiet = hasOption(parsed, '-q') || hasOption(parsed, '--quiet')
  state.repository_initialized = true
  state.head = { type: 'branch', name: branch, target: state.branches?.[branch] ?? null }
  state.branches ??= {}
  state.branches[branch] ??= null
  if (!reinitialized) {
    state.commits = []
    state.staging = {}
    // `git init` only adds the .git metadata; existing files stay in place as
    // untracked work so an onboarding workflow can `git add .` + commit them.
    // Do NOT wipe working_tree here.
    state.conflicts = []
    state.remotes = {}
    state.remote_branches = {}
    state.upstream_tracking = {}
  }
  setOperationMetadata(state, {
    last_init_branch: branch,
    // Curriculum evaluation rules assert on these keys; keep them in sync.
    last_init_initial_branch: branch,
    last_init_directory: directory,
    last_init_current_directory: directory === null,
    last_init_quiet: quiet,
    last_init_reinitialized: reinitialized,
    // Retain the original key for existing authored content and snapshots.
    repository_reinitialized: reinitialized,
  })
  return {
    command: 'init',
    stdout: quiet
      ? ''
      : `${reinitialized ? 'Reinitialized existing' : 'Initialized empty'} Git repository${parsed.args[0] ? ` in ${parsed.args[0]}/.git/` : ''}`,
  }
}

export function gitClone(state: MutableRepositoryState, parsed: ParsedGitCommand): CommandOutcome {
  if (state.repository_initialized) {
    throw new SimulatorCommandError("fatal: destination path already exists and is not an empty directory.", 128)
  }
  const url = parsed.args[0]
  const directory = parsed.args[1] ?? defaultCloneDirectory(url)
  const remoteName = 'origin'
  state.repository_initialized = true
  state.remotes = { [remoteName]: url }
  state.remote_branches = {}
  applyRemoteFixtureBranches(state)
  materializeRemoteCommits(state)

  const branchValue = String(optionValues(parsed, '-b', '--branch').at(-1) ?? '')
  const defaultRemoteBranch = defaultRemoteBranchFor(state, remoteName)
  const selectedRemoteBranch = branchValue ? `${remoteName}/${branchValue}` : defaultRemoteBranch
  if (!(selectedRemoteBranch in (state.remote_branches ?? {}))) {
    throw new SimulatorCommandError(`fatal: Remote branch ${branchValue} not found in upstream ${remoteName}`)
  }
  const selectedTarget = state.remote_branches?.[selectedRemoteBranch] ?? null
  const selectedBranch = selectedRemoteBranch.split('/').slice(1).join('/') || 'main'
  state.branches = { [selectedBranch]: selectedTarget }
  state.head = { type: 'branch', name: selectedBranch, target: selectedTarget }
  state.upstream_tracking = { [selectedBranch]: selectedRemoteBranch }
  state.staging = {}
  state.working_tree = {}
  state.conflicts = []
  const depthRaw = optionValues(parsed, '--depth').at(-1)
  const depth = depthRaw && depthRaw !== true ? Number(depthRaw) : null
  if (depth && depth > 0) truncateShallow(state, selectedTarget, depth)
  setOperationMetadata(state, {
    last_clone_url: url,
    last_clone_directory: directory,
    // Curriculum evaluation rules assert on these keys; keep them in sync.
    last_clone_destination: directory,
    last_clone_branch: selectedBranch,
    last_clone_depth: depth,
    last_clone_shallow: depth !== null,
  })
  return { command: 'clone', stdout: `Cloning into '${directory}'...` }
}

// Shallow clone: keep only `depth` commits back from the tip and graft the oldest
// kept commit into a root (parents cleared), so `--depth 1` yields a single-tip
// history - what curriculum 1.A hard ("clone shallow") asserts on.

function truncateShallow(state: MutableRepositoryState, tip: string | null, depth: number) {
  const kept: string[] = []
  let current: string | null = tip
  while (current && kept.length < depth) {
    kept.push(current)
    current = commitById(state, current)?.parents?.[0] ?? null
  }
  const keptSet = new Set(kept)
  state.commits = (state.commits ?? []).filter((commit) => keptSet.has(commit.id))
  const oldest = commitById(state, kept.at(-1) ?? null)
  if (oldest) oldest.parents = []
}

function defaultCloneDirectory(url: string) {
  const tail = url.split('/').filter(Boolean).at(-1) ?? 'repository'
  return tail.replace(/\.git$/, '') || 'repository'
}

function defaultRemoteBranchFor(state: MutableRepositoryState, remote: string) {
  const fixture = isRecord(state.remote_fixtures) ? state.remote_fixtures : {}
  const defaultName = String(fixture.default_branch ?? `${remote}/main`)
  if (defaultName in (state.remote_branches ?? {})) return defaultName
  const mainRef = `${remote}/main`
  if (mainRef in (state.remote_branches ?? {})) return mainRef
  return Object.keys(state.remote_branches ?? {}).sort()[0] ?? mainRef
}

export function gitConfig(state: MutableRepositoryState, parsed: ParsedGitCommand): CommandOutcome {
  const getOutcome = configGet(state, parsed)
  if (getOutcome) return getOutcome
  if (hasOption(parsed, '--list') || hasOption(parsed, '-l')) {
    // Read-only: do not create a `config` key, or the listing would mutate state
    // and a `config --list` scenario could never assert repository_state_unchanged.
    return {
      command: 'config',
      stdout: Object.entries(state.config ?? {})
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, value]) => `${key}=${value}`)
        .join('\n'),
    }
  }
  state.config ??= {}
  const [key, value] = parsed.args
  state.config[key] = value
  const metadata: Record<string, RepositoryValue> = {
    last_config_scope: 'global',
    last_config_key: key,
    last_config_value: value,
  }
  if (key === 'merge.tool') metadata.configured_merge_tool = value
  setOperationMetadata(state, metadata)
  return { command: 'config', stdout: '' }
}
