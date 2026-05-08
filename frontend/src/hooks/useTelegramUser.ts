import { retrieveLaunchParamsFp } from '@tma.js/sdk-react'

const WEB_NAME_KEY = 'sphinx_web_name'
const ANON_ID_KEY = 'sphinx_anon_id'

interface TelegramUser {
  id: number
  firstName: string
  username?: string
}

export function getTelegramUser(): TelegramUser | null {
  try {
    const result = retrieveLaunchParamsFp()
    if (result._tag === 'Left') return null
    const user = result.right.tgWebAppData?.user
    if (!user) return null
    return { id: user.id, firstName: user.first_name, username: user.username }
  } catch {
    return null
  }
}

export function isInTelegram(): boolean {
  return getTelegramUser() !== null
}

export function getWebName(): string {
  return localStorage.getItem(WEB_NAME_KEY) ?? ''
}

export function setWebName(name: string): void {
  localStorage.setItem(WEB_NAME_KEY, name.trim())
}

export function resolveTelegramId(): string {
  const user = getTelegramUser()
  if (user) return String(user.id)

  const existing = localStorage.getItem(ANON_ID_KEY)
  if (existing) return existing
  const generated = `anon_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  localStorage.setItem(ANON_ID_KEY, generated)
  return generated
}
