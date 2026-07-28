import { apiClient, type ApiEnvelope } from '@/api/client'
import type { LoginPayload, RegisterPayload, TokenResponse, UserSummary } from '@/types/auth'

export async function register(payload: RegisterPayload): Promise<UserSummary> {
  const response = await apiClient.post<ApiEnvelope<UserSummary>>('/auth/register', payload)
  return response.data.data
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const response = await apiClient.post<ApiEnvelope<TokenResponse>>('/auth/login', payload)
  return response.data.data
}

export async function getCurrentUser(): Promise<UserSummary> {
  const response = await apiClient.get<ApiEnvelope<UserSummary>>('/auth/me')
  return response.data.data
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/logout')
}

export async function updateProfile(payload: { display_name?: string }): Promise<UserSummary> {
  const response = await apiClient.put<ApiEnvelope<UserSummary>>('/auth/me', payload)
  return response.data.data
}

export async function uploadAvatar(file: File): Promise<UserSummary> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post<ApiEnvelope<UserSummary>>('/auth/me/avatar', formData)
  return response.data.data
}
