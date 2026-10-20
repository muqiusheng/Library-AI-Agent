import axios from 'axios'

import type { ApiErrorPayload } from '@/types/api'

export function getApiErrorMessage(error: unknown, fallback = '请求失败，请稍后重试'): string {
  if (!axios.isAxiosError<ApiErrorPayload>(error)) return fallback
  if (!error.response) return '无法访问后端接口，请检查后端地址、开发代理或跨域配置'
  return error.response.data?.error?.message || fallback
}
