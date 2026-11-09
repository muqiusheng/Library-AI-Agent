import { listMessages } from '@/api/conversations'
import type { ConversationSummary } from '@/types/conversation'

export interface ConversationStarter {
  id: string
  label: string
  message: string
  conversationId?: string
}

export const CONTINUE_READING = '我想继续之前的阅读目标，请结合我们之前讨论的需求，推荐下一步适合的馆藏图书。'

export const DEFAULT_STARTERS: ConversationStarter[] = [
  { id: 'learn', label: '入门一个新领域', message: '入门一个新领域' },
  { id: 'course', label: '找课程或考试参考书', message: '找课程或考试参考书' },
  { id: 'project', label: '为项目或论文找资料', message: '为项目或论文找资料' },
  { id: 'interest', label: '按兴趣找几本好书', message: '按兴趣找几本好书' }
]

const genericMessages = new Set([...DEFAULT_STARTERS.map(item => item.message), CONTINUE_READING])

// Only explicit, recent user requests qualify; a profile or chat title alone is not evidence.
export async function loadConversationStarters(
  conversations: ConversationSummary[], activeId: string | null, now = Date.now()
): Promise<ConversationStarter[]> {
  const recent = conversations.filter(item => {
    const age = now - Date.parse(item.updated_at)
    return item.id !== activeId && !item.archived_at && age >= 0 && age <= 30 * 86400000
  }).sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at)).slice(0, 8)
  const histories = await Promise.allSettled(recent.map(item => listMessages(item.id)))
  const personalized: ConversationStarter[] = []
  const seen = new Set<string>()
  for (const [index, history] of histories.entries()) {
    if (history.status !== 'fulfilled') continue
    const goal = [...history.value].reverse().find(item => {
      const text = item.content.trim()
      return item.role === 'user' && !genericMessages.has(text) && text.length >= 5
        && text.length <= 200
        && /(?:我想学|想学习|学习.{2,}|入门.{2,}|(?:推荐|找|寻找).{0,40}(?:书|教材|资料|小说|读物)|推荐几本.{2,}|(?:课程|考试|项目|论文).{0,40}(?:书|阅读|资料))/.test(text)
        && !/^(?:请|帮我)?推荐几本(?:好)?书[。！？]?$/u.test(text)
        && !/^(?:继续|再推荐|换一|不要|取消|只看|我想继续)/.test(text)
    })?.content.trim()
    if (!goal) continue
    const key = goal.replace(/[\s，。！？、,.!?]/g, '').toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    personalized.push({ id: recent[index].id, label: `继续：${goal}`, message: CONTINUE_READING, conversationId: recent[index].id })
    if (personalized.length === 2) break
  }
  if (!personalized.length) return [...DEFAULT_STARTERS]
  const generic = personalized.length === 1
    ? [DEFAULT_STARTERS[0], DEFAULT_STARTERS[1], DEFAULT_STARTERS[3]]
    : [DEFAULT_STARTERS[0], { ...DEFAULT_STARTERS[3], label: '换个兴趣找书' }]
  return [...personalized, ...generic]
}

export async function sendConversationStarter(
  starter: ConversationStarter,
  conversation: { selectConversation: (id: string) => Promise<void>; send: (text: string) => Promise<void> }
): Promise<void> {
  if (starter.conversationId) await conversation.selectConversation(starter.conversationId)
  await conversation.send(starter.message)
}
