import { apiClient, type ApiEnvelope } from '@/api/client'
import type { ProfileDetailData, ProfileMemoryData, ProfileUpdatePayload } from '@/types/profile'

export async function getProfile(includeHistory = false): Promise<ProfileDetailData> {
  const response = await apiClient.get<ApiEnvelope<ProfileDetailData>>('/profile', {
    params: { include_history: includeHistory }
  })
  return response.data.data
}

export async function updateProfile(payload: ProfileUpdatePayload): Promise<ProfileDetailData> {
  const response = await apiClient.patch<ApiEnvelope<ProfileDetailData>>('/profile', payload)
  return response.data.data
}

export async function updateMemory(id: string, value: unknown): Promise<ProfileMemoryData> {
  const response = await apiClient.patch<ApiEnvelope<ProfileMemoryData>>(`/profile/memories/${id}`, {
    value_json: value
  })
  return response.data.data
}

export async function deleteMemory(id: string): Promise<void> {
  await apiClient.delete(`/profile/memories/${id}`)
}
