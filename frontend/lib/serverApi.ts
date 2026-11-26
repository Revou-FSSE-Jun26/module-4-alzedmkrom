import 'server-only'
import { headers } from 'next/headers'
import { redirect } from 'next/navigation'
import { apiRequest } from '@/lib/apiClient'
import { ApiError } from '@/lib/errors'
import { getSessionToken } from '@/lib/serverSession'
import { loginPath, PATHNAME_HEADER } from '@/lib/session'

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.statusCode === 401
}

/** The path and query of the request, set by proxy.ts. Falls back to `/`. */
async function currentPath(): Promise<string> {
  const store = await headers()
  return store.get(PATHNAME_HEADER) ?? '/'
}

export const serverApi = {
  /**
   * GET for Server Components (FE-AUTH-04). Redirects to the login page with the
   * current path as `next` when there is no session token or when the API answers
   * 401. Every other error is rethrown.
   *
   * `redirect()` runs after the try/catch, so its signal never passes through a
   * try block in this module or in a caller.
   */
  async get<T>(path: string): Promise<T> {
    const token = await getSessionToken()
    if (token === null) {
      redirect(loginPath({ next: await currentPath() }))
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
      redirect(loginPath({ next: await currentPath(), sessionExpired: true }))
    }
    return response.data
  },

  /**
   * GET for routes that also serve Anonymous visitors (BE-AUTH-04), such as public boards.
   * Sends the token when one exists. Without a token it sends no Authorization header and
   * never redirects. A 401 with a token means the session expired and redirects like `get`.
   */
  async getOptional<T>(path: string): Promise<T> {
    const token = await getSessionToken()
    let response: { data: T } | null = null
    try {
      response = { data: await apiRequest<T>('GET', path, { token }) }
    } catch (error) {
      if (!isUnauthorized(error) || token === null) {
        throw error
      }
    }
    if (response === null) {
      redirect(loginPath({ next: await currentPath(), sessionExpired: true }))
    }
    return response.data
  },
}
