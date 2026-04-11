import { retrieveLaunchParamsFp } from '@tma.js/sdk-react'

interface TelegramUser {
  id: number
  firstName: string
  username?: string
}

export function getTelegramUser(): TelegramUser | null {
  const result = retrieveLaunchParamsFp()
  if (result._tag === 'Left') return null

  const user = result.right.tgWebAppData?.user
  if (!user) return null

  return {
    id: user.id,
    firstName: user.first_name,
    username: user.username,
  }
}

export function resolveTelegramId(): string {
  const user = getTelegramUser()
  if (user) return String(user.id)

  const key = 'sphinx_anon_id'
  const existing = localStorage.getItem(key)
  if (existing) return existing
  const generated = `anon_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  localStorage.setItem(key, generated)
  return generated
}
