"use client";

import { useMemo } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/lib/apiClient";

export interface UseApi {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown): Promise<T>;
  patch<T>(path: string, body: unknown): Promise<T>;
  delete<T>(path: string): Promise<T>;
}

// Binds the Auth_Context token to every apiClient call, so components never
// pass a token themselves (Requirement 5.3, decision F1). The object is
// rebuilt only when the token changes.
export function useApi(): UseApi {
  const { token } = useAuth();

  return useMemo<UseApi>(
    () => ({
      get<T>(path: string) {
        return apiClient.get<T>(path, token);
      },
      post<T>(path: string, body?: unknown) {
        return apiClient.post<T>(path, body, token);
      },
      patch<T>(path: string, body: unknown) {
        return apiClient.patch<T>(path, body, token);
      },
      delete<T>(path: string) {
        return apiClient.delete<T>(path, token);
      },
    }),
    [token],
  );
}
