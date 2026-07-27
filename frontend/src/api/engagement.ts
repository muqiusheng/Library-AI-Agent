import { apiClient } from '@/api/client'

export type FeedbackType = 'like' | 'not_interested' | 'too_hard' | 'too_easy' | 'read'
export type BookState = 'want_to_read' | 'reading' | 'completed'

export async function sendFeedback(
  setId: string,
  bookId: string,
  type: FeedbackType
): Promise<void> {
  await apiClient.post(`/recommendations/${setId}/feedback`, { book_id: bookId, type })
}

export async function setBookState(bookId: string, state: BookState): Promise<void> {
  await apiClient.put(`/user-books/${bookId}/state`, { state })
}
