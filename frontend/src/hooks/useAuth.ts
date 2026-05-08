import { useState, useEffect, useCallback } from 'react'
import type { UserOut } from '../api/auth'
import { getMe, telegramAuth } from '../api/auth'
import { getTelegramUser } from './useTelegramUser'

const TOKEN_KEY = 'sphinx_token'
const USER_ID_KEY = 'sphinx_user_id'

export interface AuthState {
  token: string | null
  user: UserOut | null
  loading: boolean
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({ token: null, user: null, loading: true })

  const saveSession = useCallback((token: string, user: UserOut) => {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_ID_KEY, String(user.id))
    setState({ token, user, loading: false })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_ID_KEY)
    setState({ token: null, user: null, loading: false })
  }, [])

  useEffect(() => {
    const init = async () => {
      // 1. Try Telegram auto-login first
      const tgUser = getTelegramUser()
      if (tgUser) {
        try {
          const storedToken = localStorage.getItem(TOKEN_KEY)
          // Validate existing token
          if (storedToken) {
            const me = await getMe(storedToken)
            if (me.telegram_id === String(tgUser.id)) {
              saveSession(storedToken, me)
              return
            }
          }
          // Issue fresh token for Telegram user
          const { access_token, user } = await telegramAuth(
            String(tgUser.id),
            tgUser.firstName,
          )
          saveSession(access_token, user)
          return
        } catch {
          // fall through to stored token check
        }
      }

      // 2. Try restoring session from stored token
      const storedToken = localStorage.getItem(TOKEN_KEY)
      if (storedToken) {
        try {
          const user = await getMe(storedToken)
          saveSession(storedToken, user)
          return
        } catch {
          localStorage.removeItem(TOKEN_KEY)
        }
      }

      setState({ token: null, user: null, loading: false })
    }

    init()
  }, [saveSession])

  return { ...state, saveSession, logout }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
