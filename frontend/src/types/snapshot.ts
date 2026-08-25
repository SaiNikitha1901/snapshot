/**
 * Mirrors backend/app/schemas/*.py field-for-field (snake_case, as the
 * API actually sends it). Git is the source of truth: these types
 * describe what the backend reports, never something the frontend
 * derives on its own.
 */

// --- objects.py --------------------------------------------------------

export interface TreeEntryRef {
  mode: string
  name: string
  oid: string
  type: 'blob' | 'tree'
}

export interface BlobObject {
  kind: 'blob'
  oid: string
  size: number
  content: string | null
  is_binary: boolean
}

export interface TreeObject {
  kind: 'tree'
  oid: string
  entries: TreeEntryRef[]
}

export interface CommitObject {
  kind: 'commit'
  oid: string
  tree_oid: string
  parent_oid: string | null
  merge_parent_oid: string | null
  author: string
  committer: string
  message: string
  is_merge: boolean
}

export interface BranchObject {
  kind: 'branch'
  name: string
  commit_oid: string | null
  is_current: boolean
}

export interface HeadObject {
  kind: 'head'
  detached: boolean
  branch_name: string | null
  commit_oid: string | null
}

export type ObjectDetail = BlobObject | TreeObject | CommitObject | BranchObject | HeadObject

// --- graph.py ------------------------------------------------------------

export interface GraphCommitNode {
  oid: string
  short_oid: string
  message_summary: string
  author: string
  parent_oid: string | null
  merge_parent_oid: string | null
  is_merge: boolean
  generation: number
  lane: number
  is_head_commit: boolean
}

export interface GraphBranchRef {
  name: string
  commit_oid: string | null
  is_current: boolean
  lane: number
}

export interface CommitGraph {
  commits: GraphCommitNode[]
  branches: GraphBranchRef[]
  head_detached: boolean
  head_commit_oid: string | null
}

// --- object_graph.py -------------------------------------------------------

export interface ObjectGraphNode {
  oid: string
  short_oid: string
  kind: 'commit' | 'tree' | 'blob'
  label: string
  depth: number
  lane: number
  is_head_commit: boolean
  is_merge: boolean | null
}

export interface ObjectGraphEdge {
  id: string
  source: string
  target: string
  label: string | null
}

export interface ObjectGraph {
  root_oid: string
  nodes: ObjectGraphNode[]
  edges: ObjectGraphEdge[]
}

// --- reflog.py -------------------------------------------------------------

export interface ReflogEntry {
  index: number
  old_oid: string | null
  new_oid: string
  short_new_oid: string
  timestamp: number
  message: string
  is_reachable: boolean
}

export interface ReflogResponse {
  entries: ReflogEntry[]
}

// --- status.py -------------------------------------------------------------

export interface RepositoryStatus {
  initialized: boolean
  head_detached: boolean
  current_branch: string | null
  current_commit_oid: string | null
  working_directory_clean: boolean
  staged_paths: string[]
  unstaged_paths: string[]
  untracked_paths: string[]
  conflicted_paths: string[]
}

// --- animation.py ------------------------------------------------------------

export type AnimationStepKind =
  | 'init_repository'
  | 'hash_blob'
  | 'write_object'
  | 'update_index'
  | 'build_tree'
  | 'write_commit'
  | 'create_branch_ref'
  | 'update_ref'
  | 'move_head'
  | 'restore_working_directory'
  | 'find_merge_base'
  | 'diff_three_way'
  | 'conflict_marker'
  | 'fast_forward'

export interface AnimationStep {
  kind: AnimationStepKind
  label: string
  detail: string | null
  object_oid: string | null
  object_type: 'blob' | 'tree' | 'commit' | null
  path: string | null
  ref_name: string | null
}

export interface AnimationSequence {
  command: string
  steps: AnimationStep[]
}

// --- learn.py ------------------------------------------------------------

export interface LearnGenerationContext {
  trigger: string
  command_name: string
  subject_oid: string | null
  branch_name: string | null
  target_branch: string | null
  extra: Record<string, string>
}

export interface LearnCard {
  trigger: string
  title: string
  core_idea: string
  why: string
  in_production_git: string | null
  explore_next: string[]
  generation_context: LearnGenerationContext | null
}

export interface LearnCardSet {
  cards: LearnCard[]
}

export interface LearnGenerateResponse {
  card: LearnCard
  source: 'gemini' | 'template'
}

// --- command.py ------------------------------------------------------------

export interface TerminalOutput {
  stdout_lines: string[]
  stderr_lines: string[]
  exit_code: number
}

export interface CommandMeta {
  raw_input: string
  name: string
  args: string[]
  recognized: boolean
}

export interface StudioResponse {
  terminal: TerminalOutput
  command: CommandMeta
  repository_status: RepositoryStatus
  commit_graph: CommitGraph
  animation: AnimationSequence | null
  focused_object: ObjectDetail | null
  learn: LearnCardSet | null
}
