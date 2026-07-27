import type { DifficultyPreference, ProfileSummary } from './auth'

export type MemorySource = 'registration' | 'conversation' | 'manual' | 'feedback'

export interface ProfileMemoryData {
  id: string
  category: string
  key: string
  value_json: unknown
  source: MemorySource
  confidence: number
  is_active: boolean
  is_user_edited: boolean
  source_message_id: string | null
  created_at: string
  updated_at: string
}

export interface ProfileDetailData {
  profile: ProfileSummary | null
  memories: ProfileMemoryData[]
}

export interface ProfileUpdatePayload {
  grade?: string
  major?: string
  foundation?: string
  learning_goals?: string[]
  interests?: string[]
  difficulty_preference?: DifficultyPreference
  courses?: string[]
  read_books?: string[]
  career_direction?: string | null
}
