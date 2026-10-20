import { defineStore } from 'pinia'
import { ref } from 'vue'

import * as api from '@/api/notifications'
import type { NotificationData } from '@/api/notifications'

export const useNotificationStore = defineStore('notifications', () => {
  const items = ref<NotificationData[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)

  async function refresh(): Promise<void> {
    loading.value = true
    try {
      ;[items.value, unreadCount.value] = await Promise.all([
        api.listNotifications(), api.getUnreadCount()
      ])
    } finally {
      loading.value = false
    }
  }

  async function read(id: string): Promise<void> {
    await api.markNotificationRead(id)
    const item = items.value.find((value) => value.id === id)
    if (item && !item.read_at) item.read_at = new Date().toISOString()
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }

  async function readAll(): Promise<void> {
    await api.markAllNotificationsRead()
    const now = new Date().toISOString()
    items.value.forEach((item) => { item.read_at ??= now })
    unreadCount.value = 0
  }

  window.addEventListener('bookpath:notification-changed', refresh)
  return { items, unreadCount, loading, refresh, read, readAll }
})
