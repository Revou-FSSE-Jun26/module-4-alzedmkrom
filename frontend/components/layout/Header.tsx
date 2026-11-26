"use client";

import { useState } from "react";
import Link from "next/link";
import { BaseButton } from "@/components/shared/BaseButton";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { useAuth } from "@/context/AuthContext";

const NAV_LINK_CLASSES =
  "rounded-lg px-3 py-1.5 text-base font-medium text-ink hover:bg-bg";

// Top bar on every Protected_Path page: brand, navigation, Notification_Bell and logout (Requirements 2.5, 18.10, 21).
export function Header() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="border-b border-line bg-surface shadow-[0_12px_28px_-18px_rgba(15,40,100,.35)]">
      <div className="prism h-[3px]" />
      <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
        <Link href="/" className="flex items-center gap-2.5 text-lg font-bold tracking-tight text-ink">
          <span
            aria-hidden="true"
            className="prism grid h-8 w-8 place-items-center rounded-[10px] text-base font-bold text-white"
          >
            R
          </span>
          RevoTask
        </Link>

        <nav
          id="main-nav"
          className={`${menuOpen ? "flex" : "hidden"} w-full flex-col gap-2 sm:ml-auto sm:flex sm:w-auto sm:flex-row sm:items-center`}
        >
          <Link href="/" className={NAV_LINK_CLASSES}>
            Dashboard
          </Link>
          {user !== null ? (
            <>
              <Link href="/my-tasks" className={NAV_LINK_CLASSES}>
                My tasks
              </Link>
              <Link href="/profile" className={NAV_LINK_CLASSES}>
                Profile
              </Link>
              <span className="px-2 py-2 text-base text-gray-600">{user.name}</span>
              <BaseButton variant="secondary" onClick={() => logout()}>
                Log out
              </BaseButton>
            </>
          ) : (
            // Anonymous visitors see Log in, not the signed-in links (FE-AUTH-03, FE-ROLE-02).
            <Link href="/login" className={NAV_LINK_CLASSES}>
              Log in
            </Link>
          )}
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
