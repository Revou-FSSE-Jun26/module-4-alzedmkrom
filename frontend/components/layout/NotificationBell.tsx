"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { useNotifications } from "@/hooks/useNotifications";
import { formatDateTime, formatUnreadCount } from "@/lib/format";
import type { Notification } from "@/types/api";

// Types whose board no longer opens for the user, so they do not link (FE-NTF-02).
const NON_LINKING_TYPES = new Set<Notification["type"]>(["board_deleted", "member_removed"]);

/** The board a notification links to, or null when it has no usable link (FE-NTF-02). */
export function notificationHref(notification: Notification): string | null {
  if (notification.board_id === null || NON_LINKING_TYPES.has(notification.type)) {
    return null;
  }
  return `/boards/${notification.board_id}`;
}

// Bell with the unread count from the API and a list of notifications as plain text (FE-NTF-02).
export function NotificationBell() {
  const router = useRouter();
  const { notifications, unreadCount, markRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const badgeText = formatUnreadCount(unreadCount);

  useEffect(() => {
    if (!open) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    const handlePointerDown = (event: MouseEvent) => {
      const container = containerRef.current;
      if (container && event.target instanceof Node && !container.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handlePointerDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, [open]);

  const handleSelect = (notification: Notification) => {
    if (!notification.is_read) {
      // markRead handles its own failures, so navigation does not wait for the PATCH.
      void markRead(notification.id);
    }
    const href = notificationHref(notification);
    setOpen(false);
    if (href !== null) {
      router.push(href);
    }
  };

  const label =
    unreadCount > 0 ? `Notifications, ${unreadCount} unread` : "Notifications";

  return (
    <div ref={containerRef} className="relative">
      <BaseButton
        variant="secondary"
        aria-label={label}
        aria-expanded={open}
        onClick={() => setOpen((previous) => !previous)}
        className="relative px-2"
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {badgeText !== null ? (
          <span className="absolute -right-2 -top-2 rounded-full bg-red-600 px-1.5 text-xs font-medium text-white">
            {badgeText}
          </span>
        ) : null}
      </BaseButton>
      {open ? (
        <div className="absolute right-0 z-20 mt-2 max-h-96 w-80 max-w-[calc(100vw-2rem)] overflow-y-auto rounded-md border border-gray-200 bg-white p-2 shadow-lg">
          {notifications.length === 0 ? (
            <p className="px-2 py-1 text-base text-gray-600">No notifications</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {notifications.map((notification) => (
                <li key={notification.id}>
                  <BaseButton
                    variant="secondary"
                    onClick={() => handleSelect(notification)}
                    className="flex w-full flex-col items-start gap-1 text-left"
                  >
                    <span className="flex w-full items-center justify-between gap-2">
                      <span className="text-base text-gray-900">{notification.message}</span>
                      {!notification.is_read ? <BaseBadge color="blue">Unread</BaseBadge> : null}
                    </span>
                    <span className="text-sm text-gray-600">
                      {formatDateTime(notification.created_at)}
                    </span>
                  </BaseButton>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
