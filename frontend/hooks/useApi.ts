"use client";

import { useMemo } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiClient, type RequestOptions } from "@/lib/apiClient";

export interface UseApi {
  get<T>(path: string): Promise<T>;
  post<T>(path: string, body?: unknown): Promise<T>;
  patch<T>(path: string, body: unknown): Promise<T>;
  delete<T>(path: string): Promise<T>;
}

// Binds the AuthContext token to every apiClient call, so components never pass a
// token themselves. The object is rebuilt only when the token changes.
export function useApi(): UseApi {
  const { token } = useAuth();
  return useMemo<UseApi>(() => {
    const options = (body?: unknown): RequestOptions => ({ token, body });
    return {
      get: <T,>(path: string) => apiClient.get<T>(path, { token }),
      post: <T,>(path: string, body?: unknown) => apiClient.post<T>(path, options(body)),
      patch: <T,>(path: string, body: unknown) => apiClient.patch<T>(path, options(body)),
      delete: <T,>(path: string) => apiClient.delete<T>(path, { token }),
    };
  }, [token]);
}
