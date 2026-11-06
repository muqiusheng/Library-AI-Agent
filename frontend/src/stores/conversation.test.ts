import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import * as api from '@/api/conversations'
import { useConversationStore } from './conversation'

vi.mock('@/api/conversations', () => ({
  listConversations: vi.fn(), createConversation: vi.fn(), listMessages: vi.fn(),
  getConstraints: vi.fn(), getRecommendation: vi.fn(), streamMessage: vi.fn()
}))

beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('sessionStorage', {
    getItem: vi.fn(() => null), setItem: vi.fn(), removeItem: vi.fn()
  })
  setActivePinia(createPinia())
  vi.mocked(api.listMessages).mockResolvedValue([])
  vi.mocked(api.listConversations).mockResolvedValue([])
  vi.mocked(api.getConstraints).mockResolvedValue({
    only_available: true, difficulty: null, excluded_terms: []
  })
  vi.mocked(api.streamMessage).mockImplementation(async (_id, _payload, onEvent) => {
    onEvent({ event: 'constraints_updated', data: { only_available: false } })
    onEvent({ event: 'text_delta', data: { content: '已取消限制' } })
  })
})

describe('conversation constraints', () => {
  it('restores the selected conversation and omits an unchanged toggle', async () => {
    const store = useConversationStore()
    await store.selectConversation('conversation-a')
    expect(store.onlyAvailable).toBe(true)
    await store.send('取消限制')
    expect(api.streamMessage).toHaveBeenCalledWith(
      'conversation-a', { content: '取消限制' }, expect.any(Function), expect.any(AbortSignal)
    )
    expect(store.onlyAvailable).toBe(false)
  })

  it('sends explicit false when the user turns off the saved filter', async () => {
    const store = useConversationStore()
    await store.selectConversation('conversation-a')
    store.onlyAvailable = false
    await store.send('再推荐一些')
    expect(vi.mocked(api.streamMessage).mock.calls[0][1]).toEqual({
      content: '再推荐一些', only_available: false
    })
  })

  it('clears a previous conversation filter when creating another conversation', async () => {
    const store = useConversationStore()
    await store.selectConversation('conversation-a')
    vi.mocked(api.createConversation).mockResolvedValue({
      id: 'conversation-b', title: '新会话', created_at: '', updated_at: '', archived_at: null
    })
    await store.newConversation()
    expect(store.onlyAvailable).toBe(false)
    expect(store.messages).toEqual([])
  })

  it('preserves the user toggle when send creates the first conversation', async () => {
    vi.mocked(api.createConversation).mockResolvedValue({
      id: 'conversation-a', title: '新会话', created_at: '', updated_at: '', archived_at: null
    })
    const store = useConversationStore()
    store.onlyAvailable = true
    await store.send('推荐 Java 图书')
    expect(vi.mocked(api.streamMessage).mock.calls[0][1]).toEqual({
      content: '推荐 Java 图书', only_available: true
    })
  })
})
