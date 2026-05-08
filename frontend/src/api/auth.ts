const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface UserOut {
  id: number
  email?: string
  name?: string
  telegram_id?: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserOut
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export const register = (email: string, password: string, name: string) =>
  request<TokenResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, name }),
  })

export const login = (email: string, password: string) =>
  request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })

export const telegramAuth = (telegram_id: string, name?: string) =>
  request<TokenResponse>('/auth/telegram', {
    method: 'POST',
    body: JSON.stringify({ telegram_id, name }),
  })

export const getMe = (token: string) =>
  request<UserOut>('/auth/me', {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  })
