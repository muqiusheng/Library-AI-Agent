import { apiClient, type ApiEnvelope } from '@/api/client'
import type { UserRole } from '@/types/auth'

export interface ManagedUserData {
  id: string
  student_no: string
  display_name: string | null
  role: UserRole
  is_active: boolean
  major: string | null
  created_at: string
  last_login_at: string | null
}

export interface RegistrationInviteStatusData {
  configured: boolean
  updated_at: string | null
}

export interface RegistrationInviteGeneratedData extends RegistrationInviteStatusData {
  code: string
}

export async function listManagedUsers(query = '') {
  const response = await apiClient.get<ApiEnvelope<ManagedUserData[]>>('/admin/users', {
    params: query ? { query } : undefined
  })
  return response.data.data
}

export async function createManagedAdmin(payload: {
  student_no: string
  display_name?: string
  password: string
}) {
  const response = await apiClient.post<ApiEnvelope<ManagedUserData>>('/admin/users/admins', payload)
  return response.data.data
}

export async function updateManagedUser(
  id: string,
  payload: { display_name?: string | null; role?: 'student' | 'admin'; is_active?: boolean }
) {
  const response = await apiClient.patch<ApiEnvelope<ManagedUserData>>(`/admin/users/${id}`, payload)
  return response.data.data
}

export async function resetManagedUserPassword(id: string, password: string) {
  const response = await apiClient.post<ApiEnvelope<ManagedUserData>>(
    `/admin/users/${id}/reset-password`,
    { password }
  )
  return response.data.data
}

export async function getRegistrationInviteStatus() {
  return (await apiClient.get<ApiEnvelope<RegistrationInviteStatusData>>(
    '/admin/users/registration-invite'
  )).data.data
}

export async function generateRegistrationInvite() {
  return (await apiClient.post<ApiEnvelope<RegistrationInviteGeneratedData>>(
    '/admin/users/registration-invite/generate'
  )).data.data
}
