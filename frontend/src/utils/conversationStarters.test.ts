import { beforeEach, describe, expect, it, vi } from 'vitest'
import { listMessages } from '@/api/conversations'
import type { ConversationSummary, MessageDto } from '@/types/conversation'
import { CONTINUE_READING, DEFAULT_STARTERS, loadConversationStarters, sendConversationStarter } from './conversationStarters'

vi.mock('@/api/conversations', () => ({ listMessages: vi.fn() }))
const now = Date.parse('2026-11-09T12:00:00Z')
const summary = (id: string, days = 0): ConversationSummary => ({
  id, title: '新会话', created_at: new Date(now).toISOString(),
  updated_at: new Date(now - days * 86400000).toISOString(), archived_at: null
})
const message = (content: string, role: MessageDto['role'] = 'user'): MessageDto => ({
  id: content, content, role, message_type: 'text', structured_payload: null, created_at: new Date(now).toISOString()
})
beforeEach(() => vi.resetAllMocks())

describe('conversation starters', () => {
  it('shows four general entries without history', async () => {
    expect(await loadConversationStarters([], null, now)).toEqual(DEFAULT_STARTERS)
    expect(listMessages).not.toHaveBeenCalled()
  })
  it('does not treat greetings, assistant suggestions or generic entries as user goals', async () => {
    vi.mocked(listMessages).mockResolvedValue([message('你好'), message('推荐几本文学书', 'assistant'), message('找课程或考试参考书')])
    expect(await loadConversationStarters([summary('a')], null, now)).toEqual(DEFAULT_STARTERS)
  })
  it('uses actual requests even if a conversation still has a default title', async () => {
    vi.mocked(listMessages).mockResolvedValue([message('推荐几本中国现当代小说')])
    const values = await loadConversationStarters([summary('a')], null, now)
    expect(values).toHaveLength(4)
    expect(values[0]).toMatchObject({ conversationId: 'a', label: '继续：推荐几本中国现当代小说' })
    expect(values.filter(item => !item.conversationId)).toHaveLength(3)
  })
  it('prioritizes recent distinct goals and keeps two general entries', async () => {
    vi.mocked(listMessages).mockImplementation(async id => [message(id === 'old' ? '我想学习建筑设计' : '推荐几本中国现当代小说')])
    const values = await loadConversationStarters([summary('old', 2), summary('new'), summary('duplicate', 1)], null, now)
    expect(values.map(item => item.id)).toEqual(['new', 'old', 'learn', 'interest'])
  })
  it('ignores expired, archived and active conversations and falls back on unavailable history', async () => {
    vi.mocked(listMessages).mockRejectedValue(new Error('offline'))
    const archived = { ...summary('archived'), archived_at: new Date(now).toISOString() }
    expect(await loadConversationStarters([summary('old', 31), archived, summary('active'), summary('failed')], 'active', now)).toEqual(DEFAULT_STARTERS)
    expect(listMessages).toHaveBeenCalledExactlyOnceWith('failed')
  })
  it('uses the latest explicit goal when a user changes topics', async () => {
    vi.mocked(listMessages).mockResolvedValue([message('我想学习 Python'), message('我想学习绘画'), message(CONTINUE_READING)])
    const values = await loadConversationStarters([summary('a')], null, now)
    expect(values[0].label).toBe('继续：我想学习绘画')
  })
  it('sends a general entry directly without switching conversations', async () => {
    const store = { selectConversation: vi.fn(), send: vi.fn().mockResolvedValue(undefined) }
    await sendConversationStarter(DEFAULT_STARTERS[0], store)
    expect(store.send).toHaveBeenCalledExactlyOnceWith('入门一个新领域')
    expect(store.selectConversation).not.toHaveBeenCalled()
  })
  it('loads original context before sending a personalized entry', async () => {
    const calls: string[] = []
    const store = {
      selectConversation: vi.fn(async () => { calls.push('select') }),
      send: vi.fn(async () => { calls.push('send') })
    }
    await sendConversationStarter({ id: 'a', conversationId: 'a', label: '继续', message: CONTINUE_READING }, store)
    expect(store.selectConversation).toHaveBeenCalledWith('a')
    expect(store.send).toHaveBeenCalledWith(CONTINUE_READING)
    expect(calls).toEqual(['select', 'send'])
  })
  it('does not send into a wrong conversation when context loading fails', async () => {
    const store = { selectConversation: vi.fn().mockRejectedValue(new Error('missing')), send: vi.fn() }
    await expect(sendConversationStarter({ id: 'a', conversationId: 'a', label: '继续', message: CONTINUE_READING }, store)).rejects.toThrow('missing')
    expect(store.send).not.toHaveBeenCalled()
  })
})
