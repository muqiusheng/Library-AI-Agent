import { apiClient, type ApiEnvelope } from '@/api/client'

export interface CourseOption {
  code: string
  name: string
  category: string
  source: 'local' | 'teaching_system' | string
}

export interface CourseCatalogQuery {
  major?: string
  grade?: string
  query?: string
}

export async function listCourseOptions(params: CourseCatalogQuery = {}): Promise<CourseOption[]> {
  const response = await apiClient.get<ApiEnvelope<CourseOption[]>>('/catalog/courses', { params })
  return response.data.data
}
