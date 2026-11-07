import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as profileApi from '@/api/profile'
import type { ProfileSummary, UserSummary } from '@/types/auth'
import type { EffectiveProfile, ProfileMemoryData, ProfileUpdatePayload } from '@/types/profile'
import { getApiErrorMessage } from '@/utils/apiError'

export const useProfileStore = defineStore('profile', () => {
  const profile = ref<ProfileSummary | null>(null)
  const memories = ref<ProfileMemoryData[]>([])
  const effectiveProfile = ref<EffectiveProfile | null>(null)
  const showHistory = ref(false)
  const displayProfile = computed(() => effectiveProfile.value ?? profile.value)
  const loading = ref(false)
  const errorMessage = ref('')
  const isComplete = computed(() => Boolean(
    profile.value?.grade && profile.value?.major && profile.value?.foundation && profile.value.learning_goals.length
  ))

  function hydrateFromUser(user: UserSummary | null): void {
    profile.value = user?.profile ?? null
    effectiveProfile.value = null
    memories.value = []
    showHistory.value = false
  }

  function clear(): void {
    profile.value = null
    memories.value = []
    effectiveProfile.value = null
    showHistory.value = false
  }

  async function load(includeHistory = showHistory.value): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const result = await profileApi.getProfile(includeHistory)
      profile.value = result.profile
      memories.value = result.memories
      effectiveProfile.value = result.effective_profile?.abilities ? result.effective_profile : null
      showHistory.value = includeHistory
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '画像加载失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function save(payload: ProfileUpdatePayload): Promise<void> {
    try {
      await profileApi.updateProfile(payload)
      await load()
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '画像保存失败')
      throw error
    }
  }

  async function editMemory(id: string, value: unknown): Promise<void> {
    try {
      await profileApi.updateMemory(id, value)
      await load()
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '记忆保存失败')
      throw error
    }
  }

  async function removeMemory(id: string): Promise<void> {
    try {
      await profileApi.deleteMemory(id)
      await load()
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '记忆删除失败')
      throw error
    }
  }

  return {
    profile, effectiveProfile, displayProfile, showHistory, memories, isComplete, loading, errorMessage,
    hydrateFromUser, clear, load, save, editMemory, removeMemory
  }
})
