import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as profileApi from '@/api/profile'
import type { ProfileSummary, UserSummary } from '@/types/auth'
import type { ProfileMemoryData, ProfileUpdatePayload } from '@/types/profile'
import { getApiErrorMessage } from '@/utils/apiError'

export const useProfileStore = defineStore('profile', () => {
  const profile = ref<ProfileSummary | null>(null)
  const memories = ref<ProfileMemoryData[]>([])
  const loading = ref(false)
  const errorMessage = ref('')
  const isComplete = computed(() => Boolean(
    profile.value?.grade && profile.value?.major && profile.value?.foundation && profile.value.learning_goals.length
  ))

  function hydrateFromUser(user: UserSummary | null): void {
    profile.value = user?.profile ?? null
  }

  function clear(): void {
    profile.value = null
    memories.value = []
  }

  async function load(includeHistory = false): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const result = await profileApi.getProfile(includeHistory)
      profile.value = result.profile
      memories.value = result.memories
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '画像加载失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function save(payload: ProfileUpdatePayload): Promise<void> {
    const result = await profileApi.updateProfile(payload)
    profile.value = result.profile
    memories.value = result.memories
  }

  async function editMemory(id: string, value: unknown): Promise<void> {
    await profileApi.updateMemory(id, value)
    await load(true)
  }

  async function removeMemory(id: string): Promise<void> {
    await profileApi.deleteMemory(id)
    await load(true)
  }

  return {
    profile, memories, isComplete, loading, errorMessage,
    hydrateFromUser, clear, load, save, editMemory, removeMemory
  }
})
