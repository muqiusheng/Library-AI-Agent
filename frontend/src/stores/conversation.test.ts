import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { watch } from 'vue'

import * as api from '@/api/conversations'
import { useConversationStore } from './conversation'
import type { AnalysisTrace } from '@/types/analysis'
import type { StreamEvent } from '@/types/conversation'

afterEach(() => vi.useRealTimers())

vi.mock('@/api/conversations', () => ({
  listConversations: vi.fn(), createConversation: vi.fn(), listMessages: vi.fn(),
  getConstraints: vi.fn(), getRecommendation: vi.fn(), streamMessage: vi.fn(), retryMessage: vi.fn()
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

function trace(status: AnalysisTrace['status'] = 'running'): AnalysisTrace {
  return {
    status, elapsed_ms: 1200,
    steps: [{ id: 'comparing', label: '正在比较适配程度', detail: '重点比较 3 本', status, elapsed_ms: 500 }],
    profile_evidence: [], comparisons: [], summary: ''
  }
}

describe('recommendation process', () => {
  it('updates the visible response and process while the request is still running', async () => {
    const store = useConversationStore()
    await store.selectConversation('conversation-a')
    let emit!: (event: StreamEvent) => void
    let release!: () => void
    vi.mocked(api.streamMessage).mockImplementation((_id, _payload, onEvent) => {
      emit = onEvent
      return new Promise<void>((resolve) => { release = resolve })
    })
    const sending = store.send('推荐 Python 图书')
    const response = store.messages[1]
    const contents: string[] = []
    const unwatch = watch(() => response.content, (content) => contents.push(content), { flush: 'sync' })
    emit({ event: 'analysis', data: { ...trace() } })
    emit({ event: 'text_delta', data: { content: '第一段' } })
    emit({ event: 'text_delta', data: { content: '第二段' } })
    expect(contents).toEqual(['第一段', '第一段第二段'])
    expect(response.pending).toBe(true)
    expect(response.analysis?.steps[0].id).toBe('comparing')
    emit({ event: 'analysis', data: { ...trace('complete') } })
    emit({ event: 'message_end', data: { message_id: 'saved-message' } })
    release()
    await sending
    expect(response.id).toBe('saved-message')
    expect(response.pending).toBe(false)
    expect(store.isStreaming).toBe(false)
    unwatch()
  })

  it('restores the saved process when reopening history', async () => {
    const saved = trace('complete')
    vi.mocked(api.listMessages).mockResolvedValue([{
      id: 'saved', role: 'assistant', content: '推荐结果', message_type: 'text',
      structured_payload: { analysis: saved }, created_at: ''
    }])
    const store = useConversationStore()
    await store.selectConversation('conversation-a')
    expect(store.messages[0].analysis).toEqual(saved)
  })

  it('freezes timing on stop and does not turn cancellation into a failure', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-07T00:00:00Z'))
    vi.mocked(api.streamMessage).mockImplementation((_id, _payload, onEvent, signal) => {
      onEvent({ event: 'analysis', data: { ...trace() } })
      return new Promise<void>((_resolve, reject) => {
        signal?.addEventListener('abort', () => reject(new DOMException('Stopped', 'AbortError')))
      })
    })
    const store = useConversationStore()
    await store.selectConversation('conversation-a')
    const sending = store.send('推荐 Python 图书')
    vi.advanceTimersByTime(3000)
    store.stop()
    await sending
    const response = store.messages[1]
    expect(response.analysis?.status).toBe('stopped')
    expect(response.analysis?.elapsed_ms).toBe(4200)
    expect(response.analysis?.steps[0].elapsed_ms).toBe(3500)
    expect(response.failed).not.toBe(true)
    expect(response.pending).toBe(false)
    expect(store.errorMessage).toBe('')
  })

  it('keeps completed steps when a stream fails', async () => {
    vi.mocked(api.streamMessage).mockImplementation(async (_id, _payload, onEvent) => {
      onEvent({ event: 'analysis', data: { ...trace() } })
      onEvent({ event: 'error', data: { message: '检索服务暂不可用' } })
    })
    const store = useConversationStore()
    await store.selectConversation('conversation-a')
    await store.send('推荐 Python 图书')
    expect(store.messages[1].analysis?.status).toBe('error')
    expect(store.messages[1].analysis?.steps[0].status).toBe('error')
    expect(store.messages[1].errorMessage).toBe('检索服务暂不可用')
  })

  it('does not label an abruptly closed connection as a completed result', async () => {
    vi.mocked(api.streamMessage).mockImplementation(async (_id, _payload, onEvent) => {
      onEvent({ event: 'analysis', data: { ...trace() } })
    })
    const store = useConversationStore()
    await store.selectConversation('conversation-a')
    await store.send('推荐 Python 图书')
    expect(store.messages[1].failed).toBe(true)
    expect(store.messages[1].analysis?.status).toBe('error')
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


async function savedTurn() {
  const saved: AnalysisTrace = { ...trace('complete'), turn_id: 'turn-1', retry_stages: ['retrieving', 'comparing', 'generating'] }
  vi.mocked(api.listMessages).mockResolvedValue([
    { id: 'turn-1', role: 'user', content: '推荐 Python 图书', message_type: 'text', structured_payload: null, created_at: '' },
    { id: 'reply-1', role: 'assistant', content: '原推荐', message_type: 'text', structured_payload: { analysis: saved }, created_at: '' }
  ])
  vi.mocked(api.retryMessage).mockImplementation(async (_conversation, _turn, payload, emit) => {
    emit({ event: 'analysis', data: { ...saved, status: 'running' } })
    emit({ event: 'text_delta', data: { content: '新推荐' } })
    emit({ event: 'analysis', data: { ...saved, excluded_profile_keys: payload.excluded_profile_keys ?? [] } })
    emit({ event: 'message_end', data: { message_id: 'reply-1' } })
  })
  const store = useConversationStore()
  await store.selectConversation('conversation-a')
  return store
}

describe('phase two actions', () => {
  it('applies an explicitly changed availability toggle to a stage retry', async () => {
    const store = await savedTurn()
    store.onlyAvailable = false
    await store.retryStage(store.messages[1], 'generating')
    expect(vi.mocked(api.retryMessage).mock.calls[0][2]).toEqual({ stage: 'generating', only_available: false })
  })

  it('retries a stage using the same reply and original user turn', async () => {
    const store = await savedTurn()
    await store.retryStage(store.messages[1], 'comparing')
    expect(api.retryMessage).toHaveBeenCalledWith('conversation-a', 'turn-1', { stage: 'comparing' }, expect.any(Function), expect.any(AbortSignal))
    expect(api.streamMessage).not.toHaveBeenCalled()
    expect(store.messages).toHaveLength(2)
    expect(store.messages[1].content).toBe('新推荐')
    expect(store.messages[1].id).toBe('reply-1')
  })

  it('distinguishes exclusions, explicit restoration, and an unchanged selection', async () => {
    const store = await savedTurn()
    await store.retryStage(store.messages[1], 'retrieving', ['topic:python'])
    expect(vi.mocked(api.retryMessage).mock.calls[0][2]).toEqual({ stage: 'retrieving', excluded_profile_keys: ['topic:python'] })
    await store.retryStage(store.messages[1], 'retrieving', [])
    expect(vi.mocked(api.retryMessage).mock.calls[1][2]).toEqual({ stage: 'retrieving', excluded_profile_keys: [] })
    await store.retryStage(store.messages[1], 'generating')
    expect(vi.mocked(api.retryMessage).mock.calls[2][2]).toEqual({ stage: 'generating' })
  })

  it('keeps the original result when the server rejects a stale retry', async () => {
    const store = await savedTurn()
    vi.mocked(api.retryMessage).mockRejectedValue(Object.assign(new Error('请对最新一轮推荐进行操作'), { name: 'ConversationStreamError' }))
    await store.retryStage(store.messages[1], 'comparing')
    expect(store.messages[1].content).toBe('原推荐')
    expect(store.messages[1].analysis?.status).toBe('complete')
    expect(store.messages[1].actionError).toBe('请对最新一轮推荐进行操作')
    expect(store.messages[1].pending).toBe(false)
  })

  it('only allows actions on the latest turn', async () => {
    const store = await savedTurn()
    store.messages.push({ id: 'turn-2', role: 'user', content: '谢谢', message_type: 'text', structured_payload: null, created_at: '' })
    expect(store.canOperate(store.messages[1])).toBe(false)
    await store.retryStage(store.messages[1], 'retrieving')
    expect(api.retryMessage).not.toHaveBeenCalled()
  })

  it('restores failed stages after reopening history', async () => {
    const failed = { ...trace('error'), turn_id: 'turn-1', error_message: '比较暂不可用' }
    vi.mocked(api.listMessages).mockResolvedValue([
      { id: 'turn-1', role: 'user', content: '找书', message_type: 'text', structured_payload: null, created_at: '' },
      { id: 'reply-1', role: 'assistant', content: '', message_type: 'text', structured_payload: { analysis: failed }, created_at: '' }
    ])
    const store = useConversationStore()
    await store.selectConversation('conversation-a')
    expect(store.messages[1].failed).toBe(true)
    expect(store.messages[1].errorMessage).toBe('比较暂不可用')
    expect(store.canOperate(store.messages[1])).toBe(true)
  })

  it('does not mark a successful retry as failed if refreshing the sidebar fails', async () => {
    const store = await savedTurn()
    vi.mocked(api.listConversations).mockRejectedValue(new Error('network'))
    await store.retryStage(store.messages[1], 'generating')
    expect(store.messages[1].failed).toBe(false)
    expect(store.messages[1].analysis?.status).toBe('complete')
  })
})
