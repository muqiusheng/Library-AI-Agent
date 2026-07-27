import { beforeEach, describe, expect, it } from 'vitest'

import {
  emptyRegistrationForm,
  loadRegistrationDraft,
  REGISTRATION_DRAFT_KEY,
  saveRegistrationDraft,
  splitTags,
  toRegisterPayload
} from './registration'

const storage = new Map<string, string>()

beforeEach(() => {
  storage.clear()
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
      removeItem: (key: string) => storage.delete(key)
    }
  })
})

describe('registration helpers', () => {
  it('normalizes comma-separated tags and removes duplicates', () => {
    expect(splitTags('Java，项目案例, Java、数据库\n')).toEqual(['Java', '项目案例', '数据库'])
  })

  it('maps the three-step form to the backend contract', () => {
    const form = {
      ...emptyRegistrationForm(),
      studentNo: '20260001',
      password: 'SafePass123!',
      grade: '大一',
      major: '计算机科学与技术',
      foundation: '零基础',
      learningGoals: 'Java 入门，完成项目'
    }
    const payload = toRegisterPayload(form)
    expect(payload.student_no).toBe('20260001')
    expect(payload.profile.learning_goals).toEqual(['Java 入门', '完成项目'])
    expect(payload.profile.difficulty_preference).toBe('progressive')
  })

  it('persists draft fields without storing passwords', () => {
    const form = {
      ...emptyRegistrationForm(),
      studentNo: '20260001',
      password: 'never-store-this-password',
      confirmPassword: 'never-store-this-password',
      registrationCode: 'never-store-this-invite',
      major: '计算机科学与技术'
    }
    saveRegistrationDraft(form, 2)
    const raw = storage.get(REGISTRATION_DRAFT_KEY) ?? ''
    expect(raw).not.toContain('never-store-this-password')
    expect(raw).not.toContain('never-store-this-invite')
    expect(loadRegistrationDraft()).toMatchObject({ studentNo: '20260001', step: 2 })
  })
})
