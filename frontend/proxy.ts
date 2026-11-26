import { NextResponse, type NextRequest } from 'next/server'
import { loginPath, PATHNAME_HEADER, SESSION_COOKIE } from '@/lib/session'

// Pages that need a session (FE-AUTH-05). Anonymous visitors are sent to login.
// Every other path, including the public board pages, stays open.
const PROTECTED_PATHS = ['/my-tasks', '/profile']

function isProtected(pathname: string): boolean {
  return PROTECTED_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`))
}

/**
 * Route guard. Redirects a request for a protected path without a session cookie
 * to `/login?next=...`. The token is not validated here: an invalid token is
 * rejected by the API and handled by the Server Components (lib/serverApi.ts).
 * Every request gets its path in a header so Server Components can build `next`.
 */
export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  const pathAndQuery = `${pathname}${request.nextUrl.search}`
  const token = request.cookies.get(SESSION_COOKIE)?.value

  if (isProtected(pathname) && (token === undefined || token.length === 0)) {
    return NextResponse.redirect(new URL(loginPath({ next: pathAndQuery }), request.url))
  }

  const requestHeaders = new Headers(request.headers)
  requestHeaders.set(PATHNAME_HEADER, pathAndQuery)
  return NextResponse.next({ request: { headers: requestHeaders } })
}

export const config = {
  matcher: [
    // Skip Next.js internals, favicon.ico and static assets by file extension.
    '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js|map|txt|xml)$).*)',
  ],
}
