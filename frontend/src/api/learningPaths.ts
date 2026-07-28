import { apiClient, type ApiEnvelope } from '@/api/client'
import type { BookState } from '@/api/engagement'
import type { LearningPathData, LearningPathStatus, LearningPathSummaryData } from '@/types/learningPath'

export async function createLearningPath(recommendationSetId: string): Promise<LearningPathData> {
  const response = await apiClient.post<ApiEnvelope<LearningPathData>>('/learning-paths', {
    recommendation_set_id: recommendationSetId
  })
  return response.data.data
}

export async function listLearningPaths(): Promise<LearningPathSummaryData[]> {
  const response = await apiClient.get<ApiEnvelope<LearningPathSummaryData[]>>('/learning-paths')
  return response.data.data
}

export async function getLearningPath(id: string): Promise<LearningPathData> {
  const response = await apiClient.get<ApiEnvelope<LearningPathData>>(`/learning-paths/${id}`)
  return response.data.data
}

export async function updatePathStatus(id: string, status: LearningPathStatus): Promise<LearningPathData> {
  const response = await apiClient.patch<ApiEnvelope<LearningPathData>>(`/learning-paths/${id}/status`, { status })
  return response.data.data
}

export async function updatePathBook(id: string, bookId: string, state: BookState): Promise<LearningPathData> {
  const response = await apiClient.patch<ApiEnvelope<LearningPathData>>(`/learning-paths/${id}/books/${bookId}`, { state })
  return response.data.data
}

export async function completePathStage(id: string, stageId: string): Promise<LearningPathData> {
  const response = await apiClient.patch<ApiEnvelope<LearningPathData>>(`/learning-paths/${id}/stages/${stageId}/complete`)
  return response.data.data
}
