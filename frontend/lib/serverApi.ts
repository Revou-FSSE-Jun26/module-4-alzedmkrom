import 'server-only'

import { redirect } from 'next/navigation'
import { apiRequest } from '@/lib/apiClient'
import { ApiError } from '@/lib/errors'
import { getSessionToken } from '@/lib/serverSession'

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.statusCode === 401
}

export const serverApi = {
  /**
   * GET for Server Components. Redirects to the login page when there is no
   * session token or when the API answers 401. Every other error is rethrown.
   *
   * `redirect()` runs after the try/catch, so the redirect signal never passes
   * through a try block in this module or in a caller.
   */
  async get<T>(path: string): Promise<T> {
    const token = await getSessionToken()
    if (token === null) {
      redirect('/login')
    }

    let response: { data: T } | null = null
    try {
      response = { data: await apiRequest<T>('GET', path, { token }) }
    } catch (error) {
      if (!isUnauthorized(error)) {
        throw error
      }
    }

    if (response === null) {
      redirect('/login?reason=session-expired')
    }
    return response.data
  },
}
