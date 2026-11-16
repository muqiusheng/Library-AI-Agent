import { apiClient } from './client'
import type { BookState } from './engagement'
import type { HoldingCard } from '@/types/recommendation'

export interface BookStatus {
  book_id: string
  wanted: boolean
  state: BookState
  heat_count: number
}
export interface InterestBook extends BookStatus {
  title: string
  responsible_person: string | null
  isbn: string | null
  holdings_count: number
  available_count: number
  rank?: number
  added_at?: string
}
export interface BookList {
  items: InterestBook[]
  total: number
  page: number
  page_size: number
}
export interface CatalogDetail extends InterestBook {
  publisher: string | null
  publication_year: number | null
  description: string | null
  holdings: HoldingCard[]
}
export async function getBookStatuses(book_ids: string[]): Promise<BookStatus[]> {
  return (await apiClient.post('/user-books/status', { book_ids })).data.data
}
export async function setInterest(bookId: string, wanted: boolean): Promise<BookStatus> {
  return (await apiClient.put(`/user-books/${bookId}/interest`, { wanted })).data.data
}
export async function getWanted(page = 1): Promise<BookList> {
  return (await apiClient.get('/user-books/wanted', { params: { page } })).data.data
}
export async function getPopular(days: number, page = 1, admin = false): Promise<BookList> {
  return (await apiClient.get(admin ? '/admin/books/popular' : '/books/popular', {
    params: { days, ...(admin ? { page } : {}) }
  })).data.data
}
export async function getCatalogDetail(id: string): Promise<CatalogDetail> {
  return (await apiClient.get(`/books/${id}`)).data.data
}
