"use client";

import { RouteError } from "@/components/shared/RouteError";

// Root error boundary. Next.js passes `reset`, not `retry`. Route-level error.tsx files reuse RouteError.
export default function Error({ reset }: { reset: () => void }) {
  return <RouteError reset={reset} />;
}
