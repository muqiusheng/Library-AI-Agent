import type { BookState } from '@/api/engagement'

export type LearningPathStatus = 'draft' | 'active' | 'completed' | 'archived'

export interface PathBookData {
  book_id: string
  title: string
  position: number
  state: BookState
}

export interface PathStageData {
  id: string
  position: number
  title: string
  objective: string
  duration_text: string
  prerequisites: string | null
  completion_criteria: string
  books: PathBookData[]
}

export interface LearningPathData {
  id: string
  title: string
  goal: string
  status: LearningPathStatus
  progress: number
  conversation_id: string | null
  created_at: string
  updated_at: string
  stages: PathStageData[]
}

export interface LearningPathSummaryData {
  id: string
  title: string
  goal: string
  status: LearningPathStatus
  progress: number
  stage_count: number
  book_count: number
  updated_at: string
}
