import type { RecommendationSetData } from './recommendation'

export interface ConversationSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  archived_at: string | null
}

export interface MessageDto {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  message_type: 'text' | 'recommendation' | 'path' | 'system'
  structured_payload: { recommendation_set_id?: string } | null
  created_at: string
}

export interface WorkspaceMessage extends MessageDto {
  pending?: boolean
  failed?: boolean
  recommendation?: RecommendationSetData
}

export type StreamStatus = 'idle' | 'understanding' | 'retrieving' | 'organizing' | 'complete' | 'error'

export interface StreamEvent {
  event: string
  data: Record<string, unknown>
}
