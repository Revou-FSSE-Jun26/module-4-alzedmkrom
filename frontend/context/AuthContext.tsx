"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { clearSessionCookie, writeSessionCookie } from "@/lib/session";
import type { User } from "@/lib/types";

export interface AuthContextValue {
  token: string | null;
  user: User | null;
  login(token: string, expiresIn: number, user: User): void;
  logout(): void;
  clearSession(): void;
  updateUser(user: User): void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export interface AuthProviderProps {
  initialToken: string | null;
  initialUser: User | null;
  children: ReactNode;
}

export function AuthProvider({
  initialToken,
  initialUser,
  children,
}: AuthProviderProps) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(initialToken);
  const [user, setUser] = useState<User | null>(initialUser);

  const login = useCallback((nextToken: string, expiresIn: number, nextUser: User) => {
    writeSessionCookie(nextToken, expiresIn);
    setToken(nextToken);
    setUser(nextUser);
  }, []);

  // F4: clears state and the cookie, with no navigation.
  const clearSession = useCallback(() => {
    setToken(null);
    setUser(null);
    clearSessionCookie();
  }, []);

  const logout = useCallback(() => {
    clearSession();
    router.replace("/login");
    router.refresh();
  }, [clearSession, router]);

  const updateUser = useCallback((nextUser: User) => {
    setUser(nextUser);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ token, user, login, logout, clearSession, updateUser }),
    [token, user, login, logout, clearSession, updateUser],
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
