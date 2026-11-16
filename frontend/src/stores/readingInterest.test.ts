import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as api from '@/api/readingInterest'
import * as engagement from '@/api/engagement'
import { useReadingInterestStore } from './readingInterest'

vi.mock('@/api/readingInterest', () => ({ getBookStatuses: vi.fn(), setInterest: vi.fn() }))
vi.mock('@/api/engagement', () => ({ setBookState: vi.fn() }))
const status = (id: string, wanted = false) => ({ book_id: id, wanted, state: 'completed' as const, heat_count: 1 })
beforeEach(() => { vi.resetAllMocks(); setActivePinia(createPinia()) })

describe('reading interest', () => {
  it('batches status loading for cards mounted together', async () => {
    vi.mocked(api.getBookStatuses).mockResolvedValue([status('a'), status('b')])
    const store = useReadingInterestStore()
    await Promise.all([store.ensure('a'), store.ensure('b'), store.ensure('a')])
    expect(api.getBookStatuses).toHaveBeenCalledTimes(1)
    expect(api.getBookStatuses).toHaveBeenCalledWith(['a', 'b'])
    expect(store.statuses.a.state).toBe('completed')
  })
  it('sends an explicit desired state and preserves progress on cancellation', async () => {
    const store = useReadingInterestStore()
    store.accept([status('a', true)])
    vi.mocked(api.setInterest).mockResolvedValue(status('a'))
    await store.toggle('a')
    expect(api.setInterest).toHaveBeenCalledWith('a', false)
    expect(store.statuses.a).toEqual(status('a'))
    expect(store.revision).toBe(1)
  })
  it('keeps the previous state after failure and allows retry', async () => {
    const store = useReadingInterestStore()
    store.accept([status('a')])
    vi.mocked(api.setInterest).mockRejectedValueOnce(new Error('offline'))
    await expect(store.toggle('a')).rejects.toThrow('offline')
    expect(store.statuses.a.wanted).toBe(false)
    expect(store.busy.a).toBe(false)
    vi.mocked(api.setInterest).mockResolvedValue(status('a', true))
    await store.toggle('a')
    expect(store.statuses.a.wanted).toBe(true)
  })
  it('ignores a previous account mutation completing after logout', async () => {
    const store = useReadingInterestStore()
    store.accept([status('a')])
    let resolve!: (value: api.BookStatus) => void
    vi.mocked(api.setInterest).mockReturnValue(new Promise(r => { resolve = r }))
    const mutation = store.toggle('a')
    store.clear()
    resolve(status('a', true))
    await mutation
    expect(store.statuses).toEqual({})
  })
  it('updates reading progress without changing interest or history count', async () => {
    const store = useReadingInterestStore()
    store.accept([status('a', true)])
    vi.mocked(engagement.setBookState).mockResolvedValue()
    vi.mocked(api.getBookStatuses).mockResolvedValue([{ ...status('a', true), state: 'reading' }])
    await store.progress('a', 'reading')
    expect(store.statuses.a.wanted).toBe(true)
    expect(store.statuses.a.heat_count).toBe(1)
    expect(api.setInterest).not.toHaveBeenCalled()
  })
})
