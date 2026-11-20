import { NextResponse, type NextRequest } from 'next/server'
import { SESSION_COOKIE } from '@/lib/session'

// Paths that never redirect, so a logged-out user can reach the login and registration forms.
const PUBLIC_PATHS = new Set(['/login', '/register'])

/**
 * Route_Guard. Redirects a request to `/login` when it targets a Protected_Path without a
 * non-empty Session_Cookie. The token is not validated here: an invalid token is rejected
 * by the API and handled by the Server Components (lib/serverApi.ts).
 */
export function proxy(request: NextRequest) {
  if (PUBLIC_PATHS.has(request.nextUrl.pathname)) {
    return NextResponse.next()
  }

  const token = request.cookies.get(SESSION_COOKIE)?.value
  if (typeof token === 'string' && token.length > 0) {
    return NextResponse.next()
  }

  return NextResponse.redirect(new URL('/login', request.url))
}

export const config = {
  matcher: [
    // Skip Next.js internals, favicon.ico and static assets by file extension.
    '/((?!_next/static|_next/image|favicon\\.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js|map|txt|xml)$).*)',
  ],
}
