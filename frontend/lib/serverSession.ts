import 'server-only'

import { cache } from 'react'
import { cookies } from 'next/headers'
import { apiRequest } from '@/lib/apiClient'
import { ApiError } from '@/lib/errors'
import { SESSION_COOKIE } from '@/lib/session'
import type { User } from '@/lib/types'

/**
 * Reads the session token from the request cookies.
 * An empty cookie value counts as no token.
 */
export const getSessionToken = cache(async (): Promise<string | null> => {
  const store = await cookies()
  const value = store.get(SESSION_COOKIE)?.value
  return value ? value : null
})

/**
 * Resolves the signed-in user for the current request.
 * No token gives a null pair without a request. A 401 from `GET /api/users/me`
 * gives a null pair without throwing. Any other ApiError is rethrown.
 */
export const getServerSession = cache(
  async (): Promise<{ token: string | null; user: User | null }> => {
    const token = await getSessionToken()
    if (token === null) {
      return { token: null, user: null }
    }

    try {
      const user = await apiRequest<User>('GET', '/api/users/me', { token })
      return { token, user }
    } catch (error) {
      if (error instanceof ApiError && error.statusCode === 401) {
        return { token: null, user: null }
      }
      throw error
    }
  },
)
