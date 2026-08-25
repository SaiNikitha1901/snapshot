import type {
  CommitGraph,
  LearnCard,
  ReflogEntry,
  RepositoryStatus,
  StudioResponse,
} from '../types/snapshot'

export function makeStatus(overrides: Partial<RepositoryStatus> = {}): RepositoryStatus {
  return {
    initialized: true,
    head_detached: false,
    current_branch: 'main',
    current_commit_oid: 'a'.repeat(40),
    working_directory_clean: true,
    staged_paths: [],
    unstaged_paths: [],
    untracked_paths: [],
    conflicted_paths: [],
    ...overrides,
  }
}

export function makeGraph(overrides: Partial<CommitGraph> = {}): CommitGraph {
  return {
    commits: [],
    branches: [],
    head_detached: false,
    head_commit_oid: null,
    ...overrides,
  }
}

export function makeLearnCard(overrides: Partial<LearnCard> = {}): LearnCard {
  return {
    trigger: 'repository_initialized',
    title: 'A repository is just a folder of hashed objects',
    core_idea: 'Core idea text.',
    why: 'Why text.',
    in_production_git: null,
    explore_next: [],
    generation_context: { trigger: 'repository_initialized', command_name: 'init', subject_oid: null, branch_name: null, target_branch: null, extra: {} },
    ...overrides,
  }
}

export function makeReflogEntry(overrides: Partial<ReflogEntry> = {}): ReflogEntry {
  return {
    index: 0,
    old_oid: 'b'.repeat(40),
    new_oid: 'a'.repeat(40),
    short_new_oid: 'a'.repeat(7),
    timestamp: 1_700_000_000,
    message: 'commit: initial',
    is_reachable: true,
    ...overrides,
  }
}

export function makeStudioResponse(overrides: Partial<StudioResponse> = {}): StudioResponse {
  return {
    terminal: { stdout_lines: ['ok'], stderr_lines: [], exit_code: 0 },
    command: { raw_input: 'init', name: 'init', args: [], recognized: true },
    repository_status: makeStatus(),
    commit_graph: makeGraph(),
    animation: null,
    focused_object: null,
    learn: null,
    ...overrides,
  }
}
