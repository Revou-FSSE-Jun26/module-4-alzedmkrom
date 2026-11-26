"use client";

import { BaseButton } from "@/components/shared/BaseButton";

interface RouteErrorProps {
  /** Next.js passes this to every error.tsx. It re-renders the route segment. */
  reset: () => void;
}

// Shared body for route error.tsx files (FE-UX-01). It shows no error text, stack, or digest.
export function RouteError({ reset }: RouteErrorProps) {
  return (
    <main className="flex min-h-[50vh] flex-col items-center justify-center gap-4 p-6 text-center">
      <h2 className="text-2xl font-semibold text-gray-900">Something went wrong.</h2>
      <p className="text-base text-gray-600">Try again. If the problem continues, reload the page.</p>
      <BaseButton onClick={() => reset()}>Try again</BaseButton>
    </main>
  );
}
