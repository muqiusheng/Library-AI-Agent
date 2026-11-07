import { describe, expect, it } from 'vitest'
import { createSSRApp } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createPinia } from 'pinia'
import AbilityProfile from '@/components/Profile/AbilityProfile.vue'
import ProfileEditor from '@/components/Profile/ProfileEditor.vue'
import { useProfileStore } from '@/stores/profile'
import { profileFixture } from '@/test/profileFixtures'
import { abilityRows, foundationText, memoryStatus, memoryValue } from './profilePresentation'

describe('effective profile presentation', () => {
  it('shows a negative ability as unlearned and unknown as uncertain, without invented scores', async () => {
    const fixture = profileFixture()
    const html = await renderToString(createSSRApp(AbilityProfile, { profile: fixture.effective_profile! }))
    expect(html).toContain('未学习')
    expect(html).toContain('尚不确定')
    expect(html).toContain('进阶水平')
    expect(html).toContain('我没学过 Python')
    expect(html).not.toContain('100')
    expect(html).not.toContain('学习活跃度')
    expect(abilityRows(fixture.effective_profile!).length).toBe(3)
  })
  it('uses effective values even when an effective list is empty', async () => {
    const fixture = profileFixture()
    const pinia = createPinia()
    const app = createSSRApp(ProfileEditor).use(pinia)
    const store = useProfileStore(pinia)
    store.profile = fixture.profile
    store.effectiveProfile = fixture.effective_profile!
    store.memories = fixture.memories
    const html = await renderToString(app)
    expect(html).toContain('软件工程')
    expect(html).not.toContain('旧兴趣')
    expect(html).not.toContain('旧目标')
    expect(html).toContain('当前生效')
    expect(html).toContain('历史版本')
    expect(foundationText(store.effectiveProfile, '旧基础')).toContain('Python：未学习')
  })
  it('history and achievement counts never change displayed ability', () => {
    const fixture = profileFixture()
    const initial = abilityRows(fixture.effective_profile!)
    fixture.memories.push(...Array(20).fill(fixture.memories[1]))
    expect(abilityRows(fixture.effective_profile!)).toEqual(initial)
    expect(memoryStatus(fixture.memories[0], fixture.effective_profile!)).toBe('当前生效')
    expect(memoryStatus(fixture.memories[1], fixture.effective_profile!)).toBe('历史版本')
  })
  it('formats arrays, legacy ability levels and empty values without dropping their meaning', () => {
    expect(memoryValue({ topic: 'Java', level: 'beginner', label: '旧标签' })).toBe('Java：有基础')
    expect(memoryValue(['Python', 'Java'])).toBe('Python、Java')
    expect(memoryValue([])).toBe('暂未设置')
  })
})
