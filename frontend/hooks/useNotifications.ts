"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import type { Notification, NotificationPage } from "@/types/api";

/** FE-NTF-01: polling interval while the tab is visible and the user is signed in. */
export const POLL_INTERVAL_MS = 30_000;

/** Notifications fetched per poll. The unread count comes from the API, not from this list. */
export const PAGE_SIZE = 20;

export interface UseNotifications {
  notifications: Notification[];
  /** `unread_count` from GET /api/notifications, which covers every page (BE-NTF-03). */
  unreadCount: number;
  markRead(id: string): Promise<void>;
  refresh(): Promise<void>;
}

interface NotificationState {
  items: Notification[];
  unreadCount: number;
}

// Polls the signed-in user's notifications (FE-NTF-01). Polling runs only while a token exists.
export function useNotifications(): UseNotifications {
  const { token } = useAuth();
  const api = useApi();
  const handleError = useErrorHandler();
  const [state, setState] = useState<NotificationState>({ items: [], unreadCount: 0 });

  // Mirrors `state` so handlers read the latest value without depending on render timing.
  const stateRef = useRef(state);
  // True while a poll or refresh request is pending. A tick that arrives meanwhile is skipped.
  const inFlight = useRef(false);
  // Keeps the error handler out of the effect dependencies, so the timer restarts only on token change.
  const handleErrorRef = useRef(handleError);

  useEffect(() => {
    handleErrorRef.current = handleError;
  }, [handleError]);

  const commit = useCallback((next: NotificationState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  // Loads the first page and applies it. `isActive` drops responses from a stopped session.
  const fetchPage = useCallback(
    async (isActive: () => boolean): Promise<void> => {
      inFlight.current = true;
      try {
        const page = await api.get<NotificationPage>(
          `/api/notifications?page=1&per_page=${PAGE_SIZE}`,
        );
        if (isActive()) {
          commit({ items: page.items, unreadCount: page.unread_count });
        }
      } finally {
        inFlight.current = false;
      }
    },
    [api, commit],
  );

  const refresh = useCallback(async (): Promise<void> => {
    if (token === null || inFlight.current) {
      return;
    }
    try {
      await fetchPage(() => true);
    } catch (error) {
      if (error instanceof ApiError && error.statusCode === 401) {
        handleErrorRef.current(error);
      }
      // Other failures keep the previous list. The next poll retries.
    }
  }, [token, fetchPage]);

  useEffect(() => {
    if (token === null) {
      return;
    }
    let active = true;
    const isActive = () => active;
    let timer: number | undefined;

    const stopPolling = () => {
      if (timer !== undefined) {
        window.clearInterval(timer);
        timer = undefined;
      }
    };

    const tick = async (): Promise<void> => {
      // Paused while the tab is hidden (FE-NTF-01). The visibility listener refreshes on return.
      if (document.hidden || inFlight.current) {
        return;
      }
      try {
        await fetchPage(isActive);
      } catch (error) {
        if (!active) {
          return;
        }
        if (error instanceof ApiError && error.statusCode === 401) {
          stopPolling();
          handleErrorRef.current(error);
        }
      }
    };

    const handleVisibility = () => {
      if (!document.hidden) {
        void tick();
      }
    };

    timer = window.setInterval(() => {
      void tick();
    }, POLL_INTERVAL_MS);
    document.addEventListener("visibilitychange", handleVisibility);
    void tick();

    return () => {
      active = false;
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [token, fetchPage]);

  // Optimistic read. The count drops at once and is restored if the PATCH fails.
  const markRead = useCallback(
    async (id: string): Promise<void> => {
      const current = stateRef.current;
      const target = current.items.find((notification) => notification.id === id);
      if (target === undefined || target.is_read) {
        return;
      }
      commit({
        items: current.items.map((notification) =>
          notification.id === id ? { ...notification, is_read: true } : notification,
        ),
        unreadCount: Math.max(0, current.unreadCount - 1),
      });
      try {
        await api.patch<Notification>(`/api/notifications/${id}/read`, undefined);
      } catch (error) {
        const latest = stateRef.current;
        commit({
          items: latest.items.map((notification) =>
            notification.id === id ? { ...notification, is_read: false } : notification,
          ),
          unreadCount: latest.unreadCount + 1,
        });
        handleErrorRef.current(error);
      }
    },
    [api, commit],
  );

  return {
    notifications: state.items,
    unreadCount: state.unreadCount,
    markRead,
    refresh,
  };
}
