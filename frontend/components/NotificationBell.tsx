"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { useNotifications } from "@/hooks/useNotifications";
import { sortByCreatedAt } from "@/lib/collections";
import { formatDateTime, formatUnreadCount } from "@/lib/format";

// Bell button with an unread count and a list of the signed-in user's notifications (Requirement 18).
export function NotificationBell() {
  const router = useRouter();
  const { items, unreadCount, markAsRead } = useNotifications();
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

  const handleSelect = (id: string, boardId: string, isRead: boolean) => {
    // markAsRead handles its own failures, so the navigation does not wait for the PATCH.
    if (!isRead) {
      void markAsRead(id);
    }
    router.push(`/boards/${boardId}`);
    setOpen(false);
  };

  return (
    <div ref={containerRef} className="relative">
      <BaseButton
        variant="secondary"
        aria-label="Notifications"
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
          <BaseBadge color="red" className="absolute -right-2 -top-2">
            {badgeText}
          </BaseBadge>
        ) : null}
      </BaseButton>

      {open ? (
        <div className="absolute right-0 z-20 mt-2 max-h-96 w-80 max-w-[calc(100vw-2rem)] overflow-y-auto rounded-md border border-gray-200 bg-white p-2 shadow-lg">
          {items.length === 0 ? (
            <p className="px-2 py-1 text-sm text-gray-600">No notifications</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {sortByCreatedAt(items, "desc").map((notification) => (
                <li key={notification.id}>
                  <BaseButton
                    variant="secondary"
                    onClick={() =>
                      handleSelect(notification.id, notification.board_id, notification.is_read)
                    }
                    className="flex w-full flex-col items-start gap-1 text-left"
                  >
                    <span className="flex w-full items-center justify-between gap-2">
                      <span className="text-sm text-gray-900">{notification.message}</span>
                      {!notification.is_read ? (
                        <BaseBadge color="blue">Unread</BaseBadge>
                      ) : null}
                    </span>
                    <span className="text-xs text-gray-500">
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
