import axios from 'axios'
import type { AnalysisResponse, AnalyzeRequest } from '../types/analysis'

const baseURL = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000/api/v1'

const api = axios.create({ baseURL, timeout: 60_000 })

/** Extract a human-friendly message from an axios error. */
export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
    if (err.code === 'ERR_NETWORK')
      return 'Cannot reach the API. Is the backend running on port 8000?'
    return err.message
  }
  return 'Something went wrong. Please try again.'
}

export async function analyzeProfile(payload: AnalyzeRequest): Promise<AnalysisResponse> {
  const { data } = await api.post<AnalysisResponse>('/analyze', payload)
  return data
}

export async function uploadProfile(file: File): Promise<AnalysisResponse> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<AnalysisResponse>('/analyze/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function improveHeadline(headline: string, skills: string[]): Promise<string> {
  const { data } = await api.post<{ headline: string }>('/assistant/headline', {
    headline,
    skills,
  })
  return data.headline
}

export async function improveAbout(payload: {
  name?: string | null
  headline?: string | null
  skills: string[]
  experience_years: number
  current_about?: string | null
}): Promise<string> {
  const { data } = await api.post<{ about: string }>('/assistant/about', payload)
  return data.about
}

export default api
