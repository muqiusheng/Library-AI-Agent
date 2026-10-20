import type { DifficultyPreference, RegisterPayload } from '@/types/auth'

export const REGISTRATION_DRAFT_KEY = 'bookpath_registration_draft_v1'

export interface RegistrationForm {
  studentNo: string
  password: string
  confirmPassword: string
  displayName: string
  registrationCode: string
  grade: string
  major: string
  foundation: string
  courses: string
  learningGoals: string
  interests: string
  difficultyPreference: DifficultyPreference
  readBooks: string
  careerDirection: string
}

export type RegistrationDraft = Omit<RegistrationForm, 'password' | 'confirmPassword' | 'registrationCode'> & {
  step: number
}

export const emptyRegistrationForm = (): RegistrationForm => ({
  studentNo: '',
  password: '',
  confirmPassword: '',
  displayName: '',
  registrationCode: '',
  grade: '',
  major: '',
  foundation: '',
  courses: '',
  learningGoals: '',
  interests: '',
  difficultyPreference: 'progressive',
  readBooks: '',
  careerDirection: ''
})

export function splitTags(value: string): string[] {
  return [...new Set(value.split(/[，,、\n]/).map((item) => item.trim()).filter(Boolean))]
}

export function toRegisterPayload(form: RegistrationForm): RegisterPayload {
  return {
    student_no: form.studentNo.trim(),
    password: form.password,
    display_name: form.displayName.trim() || undefined,
    registration_code: form.registrationCode.trim() || undefined,
    profile: {
      grade: form.grade.trim(),
      major: form.major.trim(),
      foundation: form.foundation.trim(),
      courses: splitTags(form.courses),
      learning_goals: splitTags(form.learningGoals),
      interests: splitTags(form.interests),
      difficulty_preference: form.difficultyPreference,
      read_books: splitTags(form.readBooks),
      career_direction: form.careerDirection.trim() || null
    }
  }
}

export function saveRegistrationDraft(form: RegistrationForm, step: number): void {
  const {
    password: _password,
    confirmPassword: _confirmPassword,
    registrationCode: _registrationCode,
    ...safeFields
  } = form
  localStorage.setItem(REGISTRATION_DRAFT_KEY, JSON.stringify({ ...safeFields, step }))
}

export function loadRegistrationDraft(): RegistrationDraft | null {
  const value = localStorage.getItem(REGISTRATION_DRAFT_KEY)
  if (!value) return null
  try {
    return JSON.parse(value) as RegistrationDraft
  } catch {
    localStorage.removeItem(REGISTRATION_DRAFT_KEY)
    return null
  }
}

export function clearRegistrationDraft(): void {
  localStorage.removeItem(REGISTRATION_DRAFT_KEY)
}
