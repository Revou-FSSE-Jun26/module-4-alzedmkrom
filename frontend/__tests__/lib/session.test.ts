import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  SESSION_COOKIE,
  buildSessionCookie,
  clearSessionCookie,
  writeSessionCookie,
} from '@/lib/session';

function captureCookieWrites(): string[] {
  const writes: string[] = [];
  Object.defineProperty(document, 'cookie', {
    configurable: true,
    get: () => '',
    set: (value: string) => {
      writes.push(value);
    },
  });
  return writes;
}

describe('session cookie', () => {
  afterEach(() => {
    // Remove the own-property override so jsdom's native cookie accessor is back.
    delete (document as unknown as Record<string, unknown>).cookie;
    vi.unstubAllGlobals();
  });

  it('uses revotask_token as the cookie name', () => {
    expect(SESSION_COOKIE).toBe('revotask_token');
  });

  it('builds a cookie without Secure over http', () => {
    expect(buildSessionCookie('abc.def_-', 3600, false)).toBe(
      'revotask_token=abc.def_-; Path=/; SameSite=Lax; Max-Age=3600',
    );
  });

  it('adds Secure only when the flag is true', () => {
    const cookie = buildSessionCookie('abc', 60, true);
    expect(cookie.split('; ')).toEqual([
      'revotask_token=abc',
      'Path=/',
      'SameSite=Lax',
      'Max-Age=60',
      'Secure',
    ]);
  });

  it('encodes characters that are unsafe in cookie values', () => {
    const cookie = buildSessionCookie('a b;c', 60, false);
    expect(cookie.startsWith('revotask_token=a%20b%3Bc;')).toBe(true);
  });

  it('never includes HttpOnly', () => {
    expect(buildSessionCookie('t', 1, true)).not.toContain('HttpOnly');
    expect(buildSessionCookie('t', 1, false)).not.toContain('HttpOnly');
  });

  it('writeSessionCookie writes the built cookie with secure false over http', () => {
    const writes = captureCookieWrites();
    writeSessionCookie('tok', 900);
    expect(writes).toEqual(['revotask_token=tok; Path=/; SameSite=Lax; Max-Age=900']);
  });

  it('writeSessionCookie sets Secure when the page is served over https', () => {
    vi.stubGlobal('location', { protocol: 'https:' });
    const writes = captureCookieWrites();
    writeSessionCookie('tok', 900);
    expect(writes[0]).toContain('; Secure');
  });

  it('clearSessionCookie expires the cookie with Max-Age=0 and Path=/', () => {
    const writes = captureCookieWrites();
    clearSessionCookie();
    expect(writes).toEqual(['revotask_token=; Path=/; SameSite=Lax; Max-Age=0']);
  });
});
