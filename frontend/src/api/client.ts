import axios from 'axios'

export interface ApiEnvelope<T> {
  success: boolean
  data: T
  request_id: string
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
  ?? '/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('bookpath_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  config.headers['X-Request-ID'] = crypto.randomUUID()
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('bookpath_access_token')
      window.dispatchEvent(new CustomEvent('bookpath:unauthorized'))
    }
    return Promise.reject(error)
  }
)
