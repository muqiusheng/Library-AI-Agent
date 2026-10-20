export interface ApiErrorPayload {
  success: false
  error: {
    code: string
    message: string
    details: Record<string, unknown>
  }
  request_id: string
}
