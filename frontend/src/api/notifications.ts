import { apiClient, type ApiEnvelope } from '@/api/client'

export interface ReservationData {
  id: string; holding_id: string; book_id: string; book_title: string; collection_location: string | null; call_number: string | null; status: 'active' | 'cancelled' | 'expired' | 'completed'; expires_at: string; is_mock: boolean; created_at: string
}
export interface NotificationData { id: string; type: string; title: string; content: string; payload: Record<string, unknown>; read_at: string | null; created_at: string }

export async function createReservation(holdingId: string) { return (await apiClient.post<ApiEnvelope<ReservationData>>('/reservations', { holding_id: holdingId })).data.data }
export async function listReservations() { return (await apiClient.get<ApiEnvelope<ReservationData[]>>('/reservations')).data.data }
export async function cancelReservation(id: string) { return (await apiClient.delete<ApiEnvelope<ReservationData>>(`/reservations/${id}`)).data.data }
export async function listNotifications() { return (await apiClient.get<ApiEnvelope<NotificationData[]>>('/notifications')).data.data }
export async function getUnreadCount() { return (await apiClient.get<ApiEnvelope<{ count: number }>>('/notifications/unread-count')).data.data.count }
export async function markNotificationRead(id: string) { await apiClient.patch(`/notifications/${id}/read`) }
export async function markAllNotificationsRead() { await apiClient.post('/notifications/read-all') }
