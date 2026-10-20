import { apiClient, type ApiEnvelope } from '@/api/client'

export interface ImportBatchData {
  id: string; file_name: string; file_hash: string; status: 'pending' | 'running' | 'succeeded' | 'failed'; stage: string; progress: number; data_version_id: string | null; statistics: Record<string, unknown>; error_summary: string | null; created_at: string; updated_at: string
}
export interface ImportIssueData { id: string; row_no: number | null; field_name: string | null; issue_type: string; raw_value: string | null; description: string; status: string }
export interface TagReviewData { id: string; book_id: string; book_title: string; tag_type: string; tag_value: string; confidence: number; source: string; model_name: string | null; prompt_version: string | null; review_status: string; reviewer_id: string | null }
export interface AdminOverviewData { users: number; conversations: number; recommendation_sets: number; published_books: number; published_holdings: number; active_reservations: number; import_batches: number; pending_tags: number; evaluation_samples: number }
export interface SystemSettingData { key: string; value: unknown; description: string }
export interface AIProviderStatusData { provider_id: string; provider: string; configured: boolean; base_url: string; chat_model: string; reasoning_model: string; key_source: string }
export interface AIProviderUpdateData { provider_id: string; provider: string; api_key?: string; base_url: string; chat_model: string; reasoning_model: string }

export async function uploadLibrary(file: File) {
  const response = await apiClient.post<ApiEnvelope<{ batch: ImportBatchData; duplicate_file: boolean }>>('/admin/imports', await file.arrayBuffer(), { headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'X-File-Name': file.name }, timeout: 120_000 })
  return response.data.data
}
export async function listImports() { return (await apiClient.get<ApiEnvelope<ImportBatchData[]>>('/admin/imports')).data.data }
export async function listImportIssues(id: string) { return (await apiClient.get<ApiEnvelope<ImportIssueData[]>>(`/admin/imports/${id}/issues`)).data.data }
export async function publishImport(id: string) { return (await apiClient.post<ApiEnvelope<ImportBatchData>>(`/admin/imports/${id}/publish`)).data.data }
export async function generateAiTags(limit = 50) { return (await apiClient.post<ApiEnvelope<{ requested_books: number; tagged_books: number; created_tags: number; cached_books: number }>>('/admin/tags/generate', { limit }, { timeout: 360_000 })).data.data }
export async function listTagReviews() { return (await apiClient.get<ApiEnvelope<TagReviewData[]>>('/admin/tags/reviews')).data.data }
export async function updateTagReview(id: string, tag_type: string, tag_value: string, review_status: string) { return (await apiClient.patch<ApiEnvelope<TagReviewData>>(`/admin/tags/reviews/${id}`, { tag_type, tag_value, review_status })).data.data }
export async function bulkReviewTags(tag_ids: string[], status: 'approved' | 'rejected') { await apiClient.post('/admin/tags/reviews/bulk', { tag_ids, status }) }
export async function getAdminOverview() { return (await apiClient.get<ApiEnvelope<AdminOverviewData>>('/admin/system/overview')).data.data }
export async function listSystemSettings() { return (await apiClient.get<ApiEnvelope<SystemSettingData[]>>('/admin/system/settings')).data.data }
export async function updateSystemSettings(settings: Record<string, unknown>) { return (await apiClient.patch<ApiEnvelope<SystemSettingData[]>>('/admin/system/settings', { settings })).data.data }
export async function getAIProviderStatus() { return (await apiClient.get<ApiEnvelope<AIProviderStatusData>>('/admin/system/ai-provider')).data.data }
export async function updateAIProvider(payload: AIProviderUpdateData) { return (await apiClient.put<ApiEnvelope<AIProviderStatusData>>('/admin/system/ai-provider', payload)).data.data }
