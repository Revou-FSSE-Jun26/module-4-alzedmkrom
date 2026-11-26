"use client";

import { RouteError } from "@/components/shared/RouteError";

// My tasks error boundary (FE-UX-01).
export default function MyTasksError({ reset }: { reset: () => void }) {
  return <RouteError reset={reset} />;
}
