'use server'

import { cookies } from 'next/headers'
import { apiRequest } from '@/lib/apiClient'
import { ApiError } from '@/lib/errors'
import { SESSION_COOKIE } from '@/lib/session'
import type { LoginResponse } from '@/types/api'

export type LoginActionResult =
  | { ok: true }
  | { ok: false; statusCode: number; message: string }

const INVALID_CREDENTIALS = 'Invalid email or password'

/**
 * Logs in through the API and stores the JWT in an httpOnly cookie (FE-AUTH-01).
 * The token never leaves the server. The browser learns only the outcome, and
 * the root layout reads the cookie on the next render (FE-AUTH-02).
 */
export async function loginAction(email: string, password: string): Promise<LoginActionResult> {
  if (typeof email !== 'string' || typeof password !== 'string') {
    return { ok: false, statusCode: 422, message: 'Check the highlighted fields.' }
  }
  let response: LoginResponse
  try {
    response = await apiRequest<LoginResponse>('POST', '/api/auth/login', {
      body: { email, password },
    })
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.statusCode === 401) {
        return { ok: false, statusCode: 401, message: INVALID_CREDENTIALS }
      }
      return { ok: false, statusCode: error.statusCode, message: error.message }
    }
    return { ok: false, statusCode: 500, message: 'Something went wrong. Please try again.' }
  }
  const store = await cookies()
  store.set(SESSION_COOKIE, response.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: response.expires_in,
  })
  return { ok: true }
}

/** Deletes the session cookie (FE-AUTH-03). The client clears AuthContext itself. */
export async function logoutAction(): Promise<void> {
  const store = await cookies()
  store.delete({ name: SESSION_COOKIE, path: '/' })
}
