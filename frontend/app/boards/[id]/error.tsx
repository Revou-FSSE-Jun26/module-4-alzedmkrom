"use client";

import { RouteError } from "@/components/shared/RouteError";

// Board error boundary (FE-UX-01, FE-PAGE-03).
export default function BoardError({ reset }: { reset: () => void }) {
  return <RouteError reset={reset} />;
}
