"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { logoutAction } from "@/app/actions/session";
import { loginPath } from "@/lib/session";
import { showSessionExpiredToast } from "@/lib/toast";
import type { User } from "@/types/api";

// The session the root layout reads from the httpOnly cookie and `GET /api/users/me` (FE-AUTH-02).
export interface AuthSession {
  token: string | null;
  user: User | null;
}

export interface AuthContextValue extends AuthSession {
  /** Stores the profile after a successful save. */
  updateUser(user: User): void;
  /** Ends the session on the client only. The cookie is not touched. */
  clearSession(): void;
  /** Deletes the cookie and sends the user to /login (FE-AUTH-03). */
  logout(): Promise<void>;
  /** Ends an expired session, shows one toast, and sends the user to /login?next= (FE-AUTH-04). */
  expireSession(): Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export interface AuthProviderProps {
  session: AuthSession;
  children: ReactNode;
}

export function AuthProvider({ session, children }: AuthProviderProps) {
  const router = useRouter();
  // Client-side changes (profile save, logout) apply to the server session they were made
  // against. When the layout re-renders with a new session object, the change is dropped.
  const [local, setLocal] = useState<{ base: AuthSession; next: AuthSession } | null>(null);
  const current = local !== null && local.base === session ? local.next : session;

  const updateUser = useCallback(
    (user: User) => {
      setLocal({ base: session, next: { token: current.token, user } });
    },
    [session, current.token],
  );

  const clearSession = useCallback(() => {
    setLocal({ base: session, next: { token: null, user: null } });
  }, [session]);

  const logout = useCallback(async () => {
    clearSession();
    await logoutAction();
    router.replace("/login");
    router.refresh();
  }, [clearSession, router]);

  const expireSession = useCallback(async () => {
    clearSession();
    await logoutAction();
    showSessionExpiredToast();
    const next = `${window.location.pathname}${window.location.search}`;
    router.replace(loginPath({ next, sessionExpired: true }));
    router.refresh();
  }, [clearSession, router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token: current.token,
      user: current.user,
      updateUser,
      clearSession,
      logout,
      expireSession,
    }),
    [current.token, current.user, updateUser, clearSession, logout, expireSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
