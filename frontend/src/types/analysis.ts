export type AnalysisStatus = 'running' | 'complete' | 'error' | 'stopped'
export type RetryStage = 'retrieving' | 'comparing' | 'generating'

export interface AnalysisStep {
  id: string
  label: string
  detail: string
  status: AnalysisStatus
  elapsed_ms: number
  reused?: boolean
  previous_elapsed_ms?: number
}

export interface ProfileEvidence {
  key: string
  label: string
  value: string
  usage: string
  source_label: string
  nature: string
  source_message_id: string | null
  updated_at: string | null
  evidence: string
  value_json?: Record<string, unknown> | string[] | string
}

export interface BookComparison {
  book_id: string
  title: string
  rank: number | null
  reason: string
  method: 'llm' | 'rule'
  description_excerpt: string
  available_count: number
  scores: Record<string, number>
  selected?: boolean
  initial_rank?: number | null
  selection_note?: string
  topics?: string[]
  difficulty?: string | null
}

export interface FilterStats {
  retrieved: number
  retained: number
  compared: number
  selected: number
  retained_from_previous: number
  steps: { id: string; label: string; applied: boolean; before: number; removed: number; remaining: number }[]
}

export interface AnalysisTrace {
  status: AnalysisStatus
  elapsed_ms: number
  steps: AnalysisStep[]
  profile_evidence: ProfileEvidence[]
  comparisons: BookComparison[]
  summary: string
  turn_id?: string | null
  filter_stats?: FilterStats
  candidates?: BookComparison[]
  excluded_profile_keys?: string[]
  excluded_profile_evidence?: ProfileEvidence[]
  retry_stages?: RetryStage[]
  retry_from?: RetryStage
  retry_note?: string
  attempt?: number
  error_message?: string
}
