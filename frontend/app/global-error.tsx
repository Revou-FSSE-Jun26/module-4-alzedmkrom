"use client";

import "./globals.css";
import { BaseButton } from "@/components/shared/BaseButton";

export default function GlobalError({ retry }: { retry: () => void }) {
  return (
    <html lang="en">
      <body>
        <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
          <h1 className="text-2xl font-semibold text-gray-900">Something went wrong.</h1>
          <BaseButton onClick={() => retry()}>Try again</BaseButton>
        </main>
      </body>
    </html>
  );
}
