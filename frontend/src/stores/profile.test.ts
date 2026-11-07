import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as api from '@/api/profile'
import { profileFixture } from '@/test/profileFixtures'
import { useProfileStore } from './profile'

vi.mock('@/api/profile', () => ({ getProfile: vi.fn(), updateProfile: vi.fn(), updateMemory: vi.fn(), deleteMemory: vi.fn() }))
beforeEach(() => {
  vi.resetAllMocks()
  setActivePinia(createPinia())
  vi.mocked(api.getProfile).mockResolvedValue(profileFixture())
})
describe('profile store', () => {
  it('uses backend effective values and does not recreate them from memory history', async () => {
    const store = useProfileStore()
    await store.load(true)
    expect(store.displayProfile?.major).toBe('软件工程')
    expect(store.displayProfile?.interests).toEqual([])
    expect(store.profile?.major).toBe('计算机科学与技术')
    expect(store.showHistory).toBe(true)
  })
  it('reloads effective profile after edits while preserving the history switch', async () => {
    const store = useProfileStore()
    await store.load(false)
    await store.editMemory('active-python', { topic: 'Python', level: 'basic' })
    expect(api.updateMemory).toHaveBeenCalledWith('active-python', { topic: 'Python', level: 'basic' })
    expect(api.getProfile).toHaveBeenLastCalledWith(false)
    await store.load(true)
    await store.removeMemory('active-python')
    expect(api.getProfile).toHaveBeenLastCalledWith(true)
  })
  it('removes a deleted ability after reloading without reviving its historical row', async () => {
    const store = useProfileStore()
    await store.load(true)
    const result = profileFixture()
    delete result.effective_profile!.abilities.python
    delete result.effective_profile!.sources['topic:python']
    result.memories.forEach(memory => { memory.is_active = false })
    vi.mocked(api.getProfile).mockResolvedValue(result)
    await store.removeMemory('active-python')
    expect(store.effectiveProfile?.abilities.python).toBeUndefined()
    expect(store.memories.length).toBe(2)
  })
  it('keeps last loaded data on failure, exposes an error, and supports retry', async () => {
    const store = useProfileStore()
    await store.load()
    vi.mocked(api.getProfile).mockRejectedValueOnce(new Error('network unavailable'))
    await expect(store.load()).rejects.toThrow()
    expect(store.loading).toBe(false)
    expect(store.displayProfile?.major).toBe('软件工程')
    expect(store.errorMessage).toBeTruthy()
    await store.load()
    expect(store.errorMessage).toBe('')
  })
  it('clears effective facts on logout and when hydrating another account', async () => {
    const store = useProfileStore()
    await store.load(true)
    store.hydrateFromUser(null)
    expect(store.effectiveProfile).toBeNull()
    store.clear()
    expect(store.memories).toEqual([])
    expect(store.showHistory).toBe(false)
  })
})
