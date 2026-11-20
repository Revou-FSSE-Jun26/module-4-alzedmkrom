export const SESSION_COOKIE = 'revotask_token';

/**
 * Builds the Set-Cookie style string for the session cookie.
 * Pure: no browser globals, so it is safe in Proxy and Client Components.
 * The cookie is intentionally not HttpOnly, because browser code writes it.
 */
export function buildSessionCookie(token: string, maxAgeSeconds: number, secure: boolean): string {
  const attributes = [
    `${SESSION_COOKIE}=${encodeURIComponent(token)}`,
    'Path=/',
    'SameSite=Lax',
    `Max-Age=${maxAgeSeconds}`,
  ];
  if (secure) {
    attributes.push('Secure');
  }
  return attributes.join('; ');
}

/** Stores the session token in `document.cookie`. Browser only. */
export function writeSessionCookie(token: string, expiresIn: number): void {
  const secure = location.protocol === 'https:';
  document.cookie = buildSessionCookie(token, expiresIn, secure);
}

/** Removes the session cookie by expiring it immediately. Browser only. */
export function clearSessionCookie(): void {
  const secure = location.protocol === 'https:';
  document.cookie = buildSessionCookie('', 0, secure);
}
