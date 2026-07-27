import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as api from '@/api/conversations'
import type {
  ConversationSummary,
  StreamEvent,
  StreamStatus,
  WorkspaceMessage
} from '@/types/conversation'
import type { RecommendationSetData } from '@/types/recommendation'
import { getApiErrorMessage } from '@/utils/apiError'

export const useConversationStore = defineStore('conversation', () => {
  const conversations = ref<ConversationSummary[]>([])
  const activeId = ref<string | null>(null)
  const messages = ref<WorkspaceMessage[]>([])
  const streamStatus = ref<StreamStatus>('idle')
  const loading = ref(false)
  const errorMessage = ref('')
  const onlyAvailable = ref(false)
  const controller = ref<AbortController | null>(null)
  const activeConversation = computed(() => conversations.value.find((item) => item.id === activeId.value) ?? null)
  const isStreaming = computed(() => !['idle', 'complete', 'error'].includes(streamStatus.value))

  async function loadConversations(): Promise<void> {
    loading.value = true
    try {
      conversations.value = await api.listConversations()
    } finally {
      loading.value = false
    }
  }

  async function newConversation(): Promise<void> {
    const created = await api.createConversation()
    conversations.value.unshift(created)
    activeId.value = created.id
    messages.value = []
  }

  async function selectConversation(id: string): Promise<void> {
    activeId.value = id
    const values = await api.listMessages(id)
    messages.value = values.map((value) => ({ ...value }))
    await Promise.all(
      messages.value.map(async (message) => {
        const setId = message.structured_payload?.recommendation_set_id
        if (setId) message.recommendation = await api.getRecommendation(setId)
      })
    )
  }

  async function removeConversation(id: string): Promise<void> {
    await api.deleteConversation(id)
    conversations.value = conversations.value.filter((item) => item.id !== id)
    if (activeId.value === id) {
      activeId.value = null
      messages.value = []
      if (conversations.value.length) await selectConversation(conversations.value[0].id)
    }
  }

  async function send(content: string): Promise<void> {
    const cleanContent = content.trim()
    if (!cleanContent || isStreaming.value) return
    if (!activeId.value) await newConversation()
    const conversationId = activeId.value as string
    const timestamp = new Date().toISOString()
    messages.value.push({
      id: crypto.randomUUID(), role: 'user', content: cleanContent, message_type: 'text',
      structured_payload: null, created_at: timestamp
    })
    const assistant: WorkspaceMessage = {
      id: crypto.randomUUID(), role: 'assistant', content: '', message_type: 'recommendation',
      structured_payload: null, created_at: timestamp, pending: true
    }
    messages.value.push(assistant)
    streamStatus.value = 'understanding'
    errorMessage.value = ''
    controller.value = new AbortController()
    try {
      await api.streamMessage(
        conversationId,
        { content: cleanContent, only_available: onlyAvailable.value },
        (event) => handleEvent(event, assistant),
        controller.value.signal
      )
      assistant.pending = false
      streamStatus.value = 'complete'
      conversations.value = await api.listConversations()
    } catch (error) {
      assistant.pending = false
      assistant.failed = true
      streamStatus.value = 'error'
      errorMessage.value = getApiErrorMessage(error, '推荐失败，请重试')
    } finally {
      controller.value = null
    }
  }

  function handleEvent(event: StreamEvent, assistant: WorkspaceMessage): void {
    if (event.event === 'message_start' && typeof event.data.status === 'string') {
      streamStatus.value = event.data.status as StreamStatus
    } else if (event.event === 'text_delta') {
      assistant.content += String(event.data.content ?? '')
    } else if (event.event === 'recommendation_ready') {
      assistant.recommendation = event.data as unknown as RecommendationSetData
    } else if (event.event === 'error') {
      throw new Error(String(event.data.message ?? '推荐失败'))
    }
  }

  function stop(): void {
    controller.value?.abort()
    streamStatus.value = 'idle'
  }

  async function retry(): Promise<void> {
    const lastUser = [...messages.value].reverse().find((message) => message.role === 'user')
    if (lastUser) {
      messages.value = messages.value.filter((message) => !message.failed)
      await send(lastUser.content)
    }
  }

  return {
    conversations, activeId, activeConversation, messages, streamStatus, loading,
    errorMessage, onlyAvailable, isStreaming, loadConversations, newConversation,
    selectConversation, removeConversation, send, stop, retry
  }
})
