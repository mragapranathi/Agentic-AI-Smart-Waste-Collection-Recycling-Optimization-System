import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: log outgoing
api.interceptors.request.use((config) => {
  return config
})

// Response interceptor: normalize errors
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Network error'
    return Promise.reject(new Error(msg))
  }
)
