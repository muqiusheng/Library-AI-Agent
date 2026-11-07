import type { AbilityLevel, EffectiveProfile, MemorySource, ProfileMemoryData } from '@/types/profile'

export const abilityLabels: Record<AbilityLevel, string> = {
  none: '未学习', basic: '有基础', intermediate: '中等水平', advanced: '进阶水平', unknown: '尚不确定'
}
export const difficultyLabels = {
  beginner: '轻松入门', progressive: '循序渐进', intermediate: '有一定挑战', advanced: '偏进阶'
}
export const sourceLabels: Record<MemorySource, string> = {
  registration: '注册填写', conversation: '对话提取', manual: '手工确认', feedback: '阅读反馈'
}
export function formatProfileDate(value?: string): string {
  if (!value || Number.isNaN(new Date(value).getTime())) return '时间未记录'
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}
export function abilityRows(profile: EffectiveProfile | null) {
  return Object.entries(profile?.abilities ?? {}).map(([key, value]) => ({
    key, ...value, source: profile?.sources?.[`topic:${key}`]
  })).sort((a, b) => a.topic.localeCompare(b.topic, 'zh-CN'))
}
export function foundationText(profile: EffectiveProfile | null, fallback: string): string {
  const rows = abilityRows(profile)
  return rows.length ? rows.map(row => `${row.topic}：${abilityLabels[row.level] ?? '尚不确定'}`).join('；') : fallback
}
export function memoryValue(value: unknown): string {
  if (Array.isArray(value)) return value.join('、') || '暂未设置'
  if (typeof value === 'object' && value !== null) {
    const item = value as Record<string, unknown>
    if (item.topic && item.level) {
      const level = item.level === 'beginner' ? 'basic' : item.level as AbilityLevel
      return `${item.topic}：${abilityLabels[level] ?? '尚不确定'}`
    }
    if (item.stage && item.path) return `完成「${item.path}」的「${item.stage}」阶段`
    return String(item.label ?? JSON.stringify(value))
  }
  return value == null || value === '' ? '暂未设置' : String(value)
}
export function memoryStatus(memory: ProfileMemoryData, effective: EffectiveProfile | null): string {
  if (!memory.is_active) return '历史版本'
  if (memory.category === 'achievement') return '学习记录'
  if (!effective) return '待同步'
  return Object.values(effective.sources).some(source => source.memory_id === memory.id) ? '当前生效' : '未采用'
}
export function categoryLabel(value: string): string {
  return ({ foundation: '学习基础', interests: '兴趣方向', interest: '兴趣方向', profile: '基础画像',
    achievement: '学习成就', grade: '年级', major: '专业', learning_goals: '学习目标',
    difficulty_preference: '难度偏好' } as Record<string, string>)[value] ?? '画像记录'
}
