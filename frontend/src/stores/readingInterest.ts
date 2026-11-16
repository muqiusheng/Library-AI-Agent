import { defineStore } from 'pinia'
import { reactive, ref } from 'vue'
import { getBookStatuses, setInterest, type BookStatus } from '@/api/readingInterest'
import { setBookState, type BookState } from '@/api/engagement'

export const useReadingInterestStore = defineStore('reading-interest', () => {
  const statuses = reactive<Record<string, BookStatus>>({})
  const busy = reactive<Record<string, boolean>>({})
  const revision = ref(0)
  const progressRevision = ref(0)
  let generation = 0
  let queued = new Set<string>()
  let scheduled: Promise<void> | null = null

  function accept(items: BookStatus[]) {
    for (const item of items) statuses[item.book_id] = item
  }
  function ensure(id: string): Promise<void> {
    if (statuses[id]) return Promise.resolve()
    queued.add(id)
    if (!scheduled) {
      const epoch = generation
      scheduled = Promise.resolve().then(async () => {
        const ids = [...queued]
        queued = new Set()
        scheduled = null
        for (let i = 0; i < ids.length; i += 100) {
          const values = await getBookStatuses(ids.slice(i, i + 100))
          if (epoch === generation) accept(values)
        }
      })
    }
    return scheduled
  }
  async function toggle(id: string) {
    if (busy[id] || !statuses[id]) return
    busy[id] = true
    const epoch = generation
    try {
      const result = await setInterest(id, !statuses[id].wanted)
      if (epoch === generation) { accept([result]); revision.value++ }
    } finally { if (epoch === generation) busy[id] = false }
  }
  async function progress(id: string, state: BookState) {
    if (busy[id]) return
    busy[id] = true
    const epoch = generation
    try {
      await setBookState(id, state)
      const values = await getBookStatuses([id])
      if (epoch === generation) { accept(values); progressRevision.value++ }
    } finally { if (epoch === generation) busy[id] = false }
  }
  async function refresh(ids: string[] = Object.keys(statuses)) {
    const epoch = generation
    for (let i = 0; i < ids.length; i += 100) {
      const values = await getBookStatuses(ids.slice(i, i + 100))
      if (epoch === generation) accept(values)
    }
    progressRevision.value++
  }
  function clear() {
    generation++
    queued.clear()
    scheduled = null
    for (const key of Object.keys(statuses)) delete statuses[key]
    for (const key of Object.keys(busy)) delete busy[key]
  }
  return { statuses, busy, revision, progressRevision, accept, ensure, toggle, progress, refresh, clear }
})
