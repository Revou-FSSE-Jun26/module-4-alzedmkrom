import { render, type RenderResult } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { vi, type Mock } from 'vitest';
import { AuthContext, type AuthContextValue } from '@/context/AuthContext';
import type { User } from '@/types/api';

export interface AuthSpies {
  logout: Mock<AuthContextValue['logout']>;
  expireSession: Mock<AuthContextValue['expireSession']>;
  clearSession: Mock<AuthContextValue['clearSession']>;
  updateUser: Mock<AuthContextValue['updateUser']>;
}

export interface RenderWithAuthOptions {
  token?: string | null;
  user?: User | null;
}

export type RenderWithAuthResult = RenderResult & { spies: AuthSpies };

export const DEFAULT_TEST_TOKEN = 'test-access-token';

export const DEFAULT_TEST_USER: User = {
  id: 'user-1',
  name: 'Test User',
  email: 'test@example.com',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

/**
 * Renders `ui` inside `AuthContext.Provider`. The provider value holds the
 * given token and user (defaults: `DEFAULT_TEST_TOKEN`, `DEFAULT_TEST_USER`)
 * and `vi.fn()` spies for `logout`, `expireSession`, `clearSession` and `updateUser`.
 * Returns the Testing Library render result together with those spies.
 */
export function renderWithAuth(
  ui: ReactElement,
  options: RenderWithAuthOptions = {},
): RenderWithAuthResult {
  const token = options.token === undefined ? DEFAULT_TEST_TOKEN : options.token;
  const user = options.user === undefined ? DEFAULT_TEST_USER : options.user;

  const spies: AuthSpies = {
    logout: vi.fn<AuthContextValue['logout']>(),
    expireSession: vi.fn<AuthContextValue['expireSession']>(),
    clearSession: vi.fn<AuthContextValue['clearSession']>(),
    updateUser: vi.fn<AuthContextValue['updateUser']>(),
  };

  const value: AuthContextValue = {
    token,
    user,
    logout: spies.logout,
    expireSession: spies.expireSession,
    clearSession: spies.clearSession,
    updateUser: spies.updateUser,
  };

  function AuthWrapper({ children }: { children: ReactNode }) {
    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
  }

  const result = render(ui, { wrapper: AuthWrapper });
  return { ...result, spies };
}
