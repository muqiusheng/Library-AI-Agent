import { defineStore } from 'pinia'
import { computed, reactive, ref, watch } from 'vue'

import * as api from '@/api/conversations'
import type {
  ConversationSummary,
  StreamEvent,
  StreamStatus,
  WorkspaceMessage
} from '@/types/conversation'
import type { RecommendationSetData } from '@/types/recommendation'
import type { AnalysisTrace, RetryStage } from '@/types/analysis'
import { getApiErrorMessage } from '@/utils/apiError'

export const useConversationStore = defineStore('conversation', () => {
  const conversations = ref<ConversationSummary[]>([])
  const activeId = ref<string | null>(sessionStorage.getItem('bookpath_active_conversation_id'))
  const messages = ref<WorkspaceMessage[]>([])
  const streamStatus = ref<StreamStatus>('idle')
  const loading = ref(false)
  const errorMessage = ref('')
  const onlyAvailable = ref(false)
  const savedOnlyAvailable = ref(false)
  const controller = ref<AbortController | null>(null)
  const activeConversation = computed(() => conversations.value.find((item) => item.id === activeId.value) ?? null)
  const isStreaming = computed(() => !['idle', 'complete', 'error'].includes(streamStatus.value))

  watch(activeId, (val) => {
    if (val) sessionStorage.setItem('bookpath_active_conversation_id', val)
    else sessionStorage.removeItem('bookpath_active_conversation_id')
  })

  async function loadConversations(): Promise<void> {
    loading.value = true
    try {
      conversations.value = await api.listConversations()
    } finally {
      loading.value = false
    }
  }

  async function newConversation(): Promise<void> {
    if (isStreaming.value) stop()
    const created = await api.createConversation()
    conversations.value.unshift(created)
    activeId.value = created.id
    messages.value = []
    onlyAvailable.value = false
    savedOnlyAvailable.value = false
  }

  async function selectConversation(id: string): Promise<void> {
    if (isStreaming.value) stop()
    activeId.value = id
    const [values, constraints] = await Promise.all([api.listMessages(id), api.getConstraints(id)])
    onlyAvailable.value = constraints.only_available
    savedOnlyAvailable.value = constraints.only_available
    messages.value = values.map((value) => ({
      ...value, analysis: value.structured_payload?.analysis,
      failed: value.structured_payload?.analysis?.status === 'error',
      stopped: value.structured_payload?.analysis?.status === 'stopped',
      errorMessage: value.structured_payload?.analysis?.error_message
    }))
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
    if (!activeId.value) {
      const requestedOnlyAvailable = onlyAvailable.value
      await newConversation()
      onlyAvailable.value = requestedOnlyAvailable
    }
    const conversationId = activeId.value as string
    const timestamp = new Date().toISOString()
    messages.value.push({
      id: crypto.randomUUID(), role: 'user', content: cleanContent, message_type: 'text',
      structured_payload: null, created_at: timestamp
    })
    const assistant = reactive<WorkspaceMessage>({
      id: crypto.randomUUID(), role: 'assistant', content: '', message_type: 'recommendation',
      structured_payload: null, created_at: timestamp, pending: true
    })
    messages.value.push(assistant)
    await streamReply(assistant, (onEvent, signal) => api.streamMessage(
      conversationId,
      {
        content: cleanContent,
        ...(onlyAvailable.value !== savedOnlyAvailable.value
          ? { only_available: onlyAvailable.value } : {})
      }, onEvent, signal
    ))
  }

  async function streamReply(
    assistant: WorkspaceMessage,
    run: (onEvent: (event: StreamEvent) => void, signal: AbortSignal) => Promise<void>
  ): Promise<void> {
    streamStatus.value = 'understanding'
    errorMessage.value = ''
    const requestController = new AbortController()
    controller.value = requestController
    try {
      await run((event) => {
        if (!requestController.signal.aborted) handleEvent(event, assistant)
      }, requestController.signal)
      if (requestController.signal.aborted) return
      if (assistant.analysis?.status === 'running') {
        assistant.errorMessage = '连接已中断，请重试'
        throw new Error(assistant.errorMessage)
      }
      assistant.pending = false
      if (controller.value === requestController) streamStatus.value = 'complete'
      // A sidebar refresh failure must not turn a completed recommendation into a failure.
      await loadConversations().catch(() => {})
    } catch (error) {
      assistant.pending = false
      if (requestController.signal.aborted) {
        assistant.stopped = true
        settleAnalysis(assistant, 'stopped')
      } else {
        assistant.failed = true
        assistant.errorMessage ||= error instanceof Error && error.name === 'ConversationStreamError'
          ? error.message : getApiErrorMessage(error, '推荐失败，请重试')
        settleAnalysis(assistant, 'error')
        if (controller.value === requestController) {
          streamStatus.value = 'error'
          errorMessage.value = assistant.errorMessage
        }
      }
    } finally {
      if (requestController.signal.aborted) {
        assistant.pending = false
        assistant.stopped = true
        settleAnalysis(assistant, 'stopped')
      }
      if (controller.value === requestController) controller.value = null
    }
  }

  function canOperate(message: WorkspaceMessage): boolean {
    const lastUser = [...messages.value].reverse().find(item => item.role === 'user')
    const lastAssistant = [...messages.value].reverse().find(item => item.role === 'assistant')
    return !isStreaming.value && Boolean(message.analysis?.turn_id)
      && lastAssistant?.id === message.id && message.analysis?.turn_id === lastUser?.id
  }

  async function retryStage(message: WorkspaceMessage, stage: RetryStage, excludedKeys?: string[]): Promise<void> {
    if (!canOperate(message) || !activeId.value || !message.analysis?.turn_id) return
    const conversationId = activeId.value
    const turnId = message.analysis.turn_id
    const previous = { ...message }
    let received = false
    message.content = ''
    message.recommendation = undefined
    message.pending = true
    message.failed = false
    message.stopped = false
    message.errorMessage = ''
    message.actionError = ''
    message.analysis = { ...message.analysis, status: 'running', steps: [], comparisons: [], candidates: [], summary: '' }
    message.analysisReceivedAt = Date.now()
    await streamReply(message, (onEvent, signal) => api.retryMessage(
      conversationId, turnId,
      {
        stage,
        ...(excludedKeys !== undefined ? { excluded_profile_keys: excludedKeys } : {}),
        ...(onlyAvailable.value !== savedOnlyAvailable.value ? { only_available: onlyAvailable.value } : {})
      },
      event => { received = true; onEvent(event) }, signal
    ))
    if (!received && message.failed) {
      const actionError = message.errorMessage
      Object.assign(message, previous, { actionError, pending: false })
    }
  }

  function handleEvent(event: StreamEvent, assistant: WorkspaceMessage): void {
    if (event.event === 'analysis') {
      assistant.analysis = event.data as unknown as AnalysisTrace
      assistant.analysisReceivedAt = Date.now()
      const lastUser = [...messages.value].reverse().find(item => item.role === 'user')
      if (lastUser && assistant.analysis.turn_id) lastUser.id = assistant.analysis.turn_id
    } else if (event.event === 'constraints_updated') {
      onlyAvailable.value = Boolean(event.data.only_available)
      savedOnlyAvailable.value = onlyAvailable.value
    } else if (event.event === 'message_start' && typeof event.data.status === 'string') {
      streamStatus.value = event.data.status as StreamStatus
    } else if (event.event === 'text_delta') {
      assistant.content += String(event.data.content ?? '')
    } else if (event.event === 'recommendation_ready') {
      assistant.recommendation = event.data as unknown as RecommendationSetData
      assistant.structured_payload = {
        ...assistant.structured_payload, recommendation_set_id: assistant.recommendation.id
      }
    } else if (event.event === 'message_end' && typeof event.data.message_id === 'string') {
      assistant.id = event.data.message_id
    } else if (event.event === 'error') {
      assistant.errorMessage = String(event.data.message ?? '推荐失败')
      throw new Error(assistant.errorMessage)
    }
  }

  function settleAnalysis(assistant: WorkspaceMessage, status: 'stopped' | 'error'): void {
    if (!assistant.analysis || assistant.analysis.status !== 'running') return
    const extra = Math.max(0, Date.now() - (assistant.analysisReceivedAt ?? Date.now()))
    assistant.analysis.elapsed_ms += extra
    const step = assistant.analysis.steps.at(-1)
    if (step?.status === 'running') {
      step.elapsed_ms += extra
      step.status = status
    }
    assistant.analysis.status = status
  }

  function stop(): void {
    controller.value?.abort()
    const assistant = [...messages.value].reverse().find((message) => message.pending)
    if (assistant) {
      assistant.pending = false
      assistant.stopped = true
      settleAnalysis(assistant, 'stopped')
    }
    streamStatus.value = 'idle'
  }

  async function retry(): Promise<void> {
    const latest = [...messages.value].reverse().find(item => item.role === 'assistant')
    if (latest && canOperate(latest) && latest.analysis?.retry_stages?.length) {
      const failed = latest.analysis.steps.at(-1)?.id as RetryStage
      await retryStage(latest, latest.analysis.retry_stages.includes(failed) ? failed : 'retrieving')
      return
    }
    const lastUser = [...messages.value].reverse().find((message) => message.role === 'user')
    if (lastUser) {
      messages.value = messages.value.filter((message) => !message.failed)
      await send(lastUser.content)
    }
  }

  function clear(): void {
    if (isStreaming.value) stop()
    conversations.value = []
    activeId.value = null
    messages.value = []
    streamStatus.value = 'idle'
    errorMessage.value = ''
    onlyAvailable.value = false
    savedOnlyAvailable.value = false
  }

  return {
    conversations, activeId, activeConversation, messages, streamStatus, loading,
    errorMessage, onlyAvailable, isStreaming, loadConversations, newConversation,
    selectConversation, removeConversation, send, stop, retry, retryStage, canOperate, clear
  }
})
