// Pure session helpers, safe to import from Server Components, Server Actions,
// the request proxy and Client Components. Cookie writes happen only in
// app/actions/session.ts, as httpOnly cookies (FE-AUTH-01).

export const SESSION_COOKIE = 'revotask_token'

/** Request header the proxy sets so Server Components know the current path. */
export const PATHNAME_HEADER = 'x-revotask-path'

/**
 * Returns `next` when it is a same-origin relative path that starts with a
 * single `/` (FE-SEC-03). Anything else, including `//host` and `/\host`,
 * falls back to `/`.
 */
export function safeNextPath(next: string | null | undefined): string {
  if (typeof next !== 'string' || next.length === 0) {
    return '/'
  }
  if (!next.startsWith('/') || next.startsWith('//') || next.startsWith('/\\')) {
    return '/'
  }
  if (next.includes('\\') || /[\u0000-\u001f]/.test(next)) {
    return '/'
  }
  return next
}

/** Builds `/login?...` with URLSearchParams (FE-SEC-03). */
export function loginPath(options: { next?: string | null; sessionExpired?: boolean } = {}): string {
  const params = new URLSearchParams()
  if (options.sessionExpired === true) {
    params.set('reason', 'session-expired')
  }
  if (options.next !== undefined && options.next !== null) {
    params.set('next', safeNextPath(options.next))
  }
  const query = params.toString()
  return query === '' ? '/login' : `/login?${query}`
}
