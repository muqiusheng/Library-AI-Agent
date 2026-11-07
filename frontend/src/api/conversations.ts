import { API_BASE_URL, apiClient, type ApiEnvelope } from '@/api/client'
import type { ConversationConstraints, ConversationSummary, MessageDto, StreamEvent } from '@/types/conversation'
import type { RecommendationSetData } from '@/types/recommendation'
import type { RetryStage } from '@/types/analysis'

export async function listConversations(): Promise<ConversationSummary[]> {
  const response = await apiClient.get<ApiEnvelope<ConversationSummary[]>>('/conversations')
  return response.data.data
}

export async function createConversation(title = '新会话'): Promise<ConversationSummary> {
  const response = await apiClient.post<ApiEnvelope<ConversationSummary>>('/conversations', { title })
  return response.data.data
}

export async function updateConversation(
  id: string,
  payload: { title?: string; archived?: boolean }
): Promise<ConversationSummary> {
  const response = await apiClient.patch<ApiEnvelope<ConversationSummary>>(`/conversations/${id}`, payload)
  return response.data.data
}

export async function deleteConversation(id: string): Promise<void> {
  await apiClient.delete(`/conversations/${id}`)
}

export async function listMessages(id: string): Promise<MessageDto[]> {
  const response = await apiClient.get<ApiEnvelope<MessageDto[]>>(`/conversations/${id}/messages`)
  return response.data.data
}

export async function getConstraints(id: string): Promise<ConversationConstraints> {
  const response = await apiClient.get<ApiEnvelope<ConversationConstraints>>(`/conversations/${id}/constraints`)
  return response.data.data
}

export async function getRecommendation(id: string): Promise<RecommendationSetData> {
  const response = await apiClient.get<ApiEnvelope<RecommendationSetData>>(`/recommendations/${id}`)
  return response.data.data
}

export async function streamMessage(
  conversationId: string,
  payload: { content: string; only_available?: boolean },
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  return streamEvents(`/conversations/${conversationId}/messages/stream`, payload, onEvent, signal)
}

export async function retryMessage(
  conversationId: string,
  messageId: string,
  payload: { stage: RetryStage; excluded_profile_keys?: string[]; only_available?: boolean },
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  return streamEvents(`/conversations/${conversationId}/messages/${messageId}/retry`, payload, onEvent, signal)
}

async function streamEvents(
  path: string, payload: unknown, onEvent: (event: StreamEvent) => void, signal?: AbortSignal
): Promise<void> {
  const token = localStorage.getItem('bookpath_access_token')
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      'X-Request-ID': crypto.randomUUID()
    },
    body: JSON.stringify(payload),
    signal
  })
  if (!response.ok || !response.body) {
    const problem = await response.json().catch(() => null)
    throw Object.assign(new Error(problem?.error?.message || '请求未完成，请稍后重试'), {
      name: 'ConversationStreamError'
    })
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
      buffer = buffer.replace(/\r\n/g, '\n')
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''
      for (const block of blocks) {
        const event = block.split('\n').find((line) => line.startsWith('event:'))?.slice(6).trim()
        const rawData = block.split('\n').find((line) => line.startsWith('data:'))?.slice(5).trim()
        if (event && rawData) onEvent({ event, data: JSON.parse(rawData) })
      }
      if (done) break
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
