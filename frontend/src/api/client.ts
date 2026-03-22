import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60_000, // 60s — LLM calls can be slow
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ?? error.message ?? 'An unexpected error occurred'
    return Promise.reject(new Error(message))
  }
)
