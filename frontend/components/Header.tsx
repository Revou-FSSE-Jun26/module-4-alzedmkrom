"use client";

import { useState } from "react";
import Link from "next/link";
import { BaseButton } from "@/components/shared/BaseButton";
import { NotificationBell } from "@/components/NotificationBell";
import { useAuth } from "@/context/AuthContext";

const NAV_LINK_CLASSES =
  "rounded-md px-2 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900";

// Top bar on every Protected_Path page: brand, navigation, Notification_Bell and logout (Requirements 2.5, 18.10, 21).
export function Header() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <Link href="/" className="text-lg font-semibold text-gray-900">
          RevoTask
        </Link>

        <nav
          id="main-nav"
          className={`${menuOpen ? "flex" : "hidden"} w-full flex-col gap-2 sm:ml-auto sm:flex sm:w-auto sm:flex-row sm:items-center`}
        >
          <Link href="/" className={NAV_LINK_CLASSES}>
            Dashboard
          </Link>
          <Link href="/my-tasks" className={NAV_LINK_CLASSES}>
            My tasks
          </Link>
          <Link href="/profile" className={NAV_LINK_CLASSES}>
            Profile
          </Link>
          <span className="px-2 py-2 text-sm text-gray-600">{user?.name}</span>
          <BaseButton variant="secondary" onClick={() => logout()}>
            Log out
          </BaseButton>
        </nav>

        <div className="ml-auto flex items-center gap-2 sm:ml-0">
          <NotificationBell />
          <BaseButton
            variant="secondary"
            aria-label="Toggle navigation"
            aria-expanded={menuOpen}
            aria-controls="main-nav"
            onClick={() => setMenuOpen((previous) => !previous)}
            className="px-2 sm:hidden"
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
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </BaseButton>
        </div>
      </div>
    </header>
  );
}
