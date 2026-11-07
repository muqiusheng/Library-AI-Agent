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
  effective_profile?: EffectiveProfile
}

export type AbilityLevel = 'none' | 'basic' | 'intermediate' | 'advanced' | 'unknown'

export interface AbilityFact {
  topic: string
  level: AbilityLevel
  basis?: string
}

export interface ProfileFactSource {
  memory_id: string
  source: MemorySource
  source_message_id: string | null
  is_user_edited: boolean
  updated_at: string
  confidence: number
  evidence?: string | null
}

export interface EffectiveProfile {
  grade: string
  major: string
  foundation: string
  foundation_background?: string
  learning_goals: string[]
  interests: string[]
  difficulty_preference: DifficultyPreference
  abilities: Record<string, AbilityFact>
  sources: Record<string, ProfileFactSource>
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
