"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Header } from "@/components/layout/Header";
import { PrismBackground } from "@/components/layout/PrismBackground";

const BARE_PATHS = ["/login", "/register"];

// Wraps every page. Hides the Header on the login and register pages (Requirements 2.5, 18.10, 21.1).
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const bare = BARE_PATHS.includes(pathname);

  return (
    <>
      <PrismBackground />
      {!bare && <Header />}
      <main className="mx-auto w-full max-w-screen-2xl px-4 py-6">{children}</main>
    </>
  );
}
