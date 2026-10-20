import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '@/api/auth'
import type { LoginPayload, RegisterPayload, UserSummary } from '@/types/auth'
import { getApiErrorMessage } from '@/utils/apiError'
import { useProfileStore } from '@/stores/profile'
import { useConversationStore } from '@/stores/conversation'

const TOKEN_KEY = 'bookpath_access_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<UserSummary | null>(null)
  const initialized = ref(false)
  const loading = ref(false)
  const errorMessage = ref('')
  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value?.role ?? ''))
  const isSuperAdmin = computed(() => user.value?.role === 'super_admin')

  function setUser(nextUser: UserSummary | null): void {
    user.value = nextUser
    useProfileStore().hydrateFromUser(nextUser)
  }

  function clearSession(): void {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    useProfileStore().clear()
    useConversationStore().clear()
  }

  async function hydrate(): Promise<void> {
    if (initialized.value) return
    if (!token.value) {
      initialized.value = true
      return
    }
    try {
      setUser(await authApi.getCurrentUser())
    } catch {
      clearSession()
    } finally {
      initialized.value = true
    }
  }

  async function login(payload: LoginPayload): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const result = await authApi.login(payload)
      token.value = result.access_token
      localStorage.setItem(TOKEN_KEY, result.access_token)
      setUser(result.user)
      initialized.value = true
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '登录失败，请检查学号和密码')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function register(payload: RegisterPayload): Promise<UserSummary> {
    loading.value = true
    errorMessage.value = ''
    try {
      return await authApi.register(payload)
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error, '注册失败，请稍后重试')
      throw error
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      if (token.value) await authApi.logout()
    } finally {
      clearSession()
      initialized.value = true
    }
  }

  window.addEventListener('bookpath:unauthorized', clearSession)

  return {
    token,
    user,
    initialized,
    loading,
    errorMessage,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    hydrate,
    login,
    register,
    logout,
    clearSession
  }
})
