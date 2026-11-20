"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import type { Notification, NotificationPage } from "@/lib/types";

export const POLL_INTERVAL_MS = 30_000;
export const PAGE_SIZE = 100;

export interface UseNotifications {
  items: Notification[];
  unreadCount: number;
  markAsRead(id: string): Promise<void>;
  refresh(): Promise<void>;
}

// Polls the notifications of the signed-in user (Requirement 18). Polling runs
// only while the Auth_Context holds a token.
export function useNotifications(): UseNotifications {
  const { token } = useAuth();
  const api = useApi();
  const handleError = useErrorHandler();

  const [items, setItems] = useState<Notification[]>([]);
  // Ids with a PATCH in flight. A poll that arrives meanwhile keeps them read (F10).
  const pendingReadIds = useRef<Set<string>>(new Set());
  // Bumped whenever polling stops or restarts, so late responses are dropped.
  const sessionRef = useRef(0);
  // Keeps the error handler out of the polling effect's dependencies, so the
  // effect only restarts when the token changes.
  const handleErrorRef = useRef(handleError);

  useEffect(() => {
    handleErrorRef.current = handleError;
  }, [handleError]);

  const fetchPage = useCallback(
    async (isCurrent: () => boolean): Promise<void> => {
      const page = await api.get<NotificationPage>(
        `/api/notifications?per_page=${PAGE_SIZE}`,
      );
      if (!isCurrent()) {
        return;
      }
      const pending = pendingReadIds.current;
      setItems(
        page.items.map((notification) =>
          pending.has(notification.id)
            ? { ...notification, is_read: true }
            : notification,
        ),
      );
    },
    [api],
  );

  // Manual refresh. Failures stay silent, the same as a non-401 poll failure.
  // A 401 is reported by the next polling tick.
  const refresh = useCallback(async (): Promise<void> => {
    if (token === null) {
      return;
    }
    const session = sessionRef.current;
    try {
      await fetchPage(() => sessionRef.current === session);
    } catch {
      // Keep the previous items. The polling tick retries.
    }
  }, [token, fetchPage]);

  useEffect(() => {
    if (token === null) {
      return;
    }

    sessionRef.current += 1;
    const session = sessionRef.current;
    const isCurrent = () => sessionRef.current === session;

    const tick = async (): Promise<void> => {
      try {
        await fetchPage(isCurrent);
      } catch (error) {
        if (!isCurrent()) {
          return;
        }
        if (error instanceof ApiError && error.statusCode === 401) {
          window.clearInterval(timer);
          handleErrorRef.current(error);
        }
      }
    };

    const timer = window.setInterval(() => {
      void tick();
    }, POLL_INTERVAL_MS);
    void tick();

    return () => {
      sessionRef.current += 1;
      window.clearInterval(timer);
    };
  }, [token, fetchPage]);

  const markAsRead = useCallback(
    async (id: string): Promise<void> => {
      pendingReadIds.current.add(id);
      setItems((previous) =>
        previous.map((notification) =>
          notification.id === id
            ? { ...notification, is_read: true }
            : notification,
        ),
      );

      try {
        await api.patch<unknown>(`/api/notifications/${id}/read`, undefined);
      } catch (error) {
        pendingReadIds.current.delete(id);
        setItems((previous) =>
          previous.map((notification) =>
            notification.id === id
              ? { ...notification, is_read: false }
              : notification,
          ),
        );
        handleErrorRef.current(error);
        return;
      }
      pendingReadIds.current.delete(id);
    },
    [api],
  );

  const unreadCount = useMemo(
    () => items.filter((notification) => !notification.is_read).length,
    [items],
  );

  return { items, unreadCount, markAsRead, refresh };
}
