"use client";

import { BaseButton } from "@/components/shared/BaseButton";

interface ErrorProps {
  error: unknown;
  retry: () => void;
}

export default function Error({ retry }: ErrorProps) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
      <h2 className="text-2xl font-semibold text-gray-900">Something went wrong.</h2>
      <BaseButton onClick={() => retry()}>Try again</BaseButton>
    </main>
  );
}
