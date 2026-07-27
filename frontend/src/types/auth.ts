export type UserRole = 'student' | 'admin' | 'super_admin'
export type DifficultyPreference = 'beginner' | 'intermediate' | 'advanced' | 'progressive'

export interface ProfileSummary {
  grade: string
  major: string
  foundation: string
  learning_goals: string[]
  interests: string[]
  difficulty_preference: DifficultyPreference
  courses: string[]
  read_books: string[]
  career_direction: string | null
}

export interface UserSummary {
  id: string
  student_no: string
  display_name: string | null
  role: UserRole
  is_active: boolean
  created_at: string
  profile: ProfileSummary | null
}

export interface RegisterPayload {
  student_no: string
  password: string
  display_name?: string
  registration_code?: string
  profile: ProfileSummary
}

export interface LoginPayload {
  student_no: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: UserSummary
}
