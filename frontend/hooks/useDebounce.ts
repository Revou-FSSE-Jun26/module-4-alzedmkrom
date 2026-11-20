"use client";

import { useEffect, useState } from "react";

// Returns `value` only after it has stayed unchanged for `delayMs`.
// Each change restarts the timer and discards the pending value, so a burst
// of changes yields one update that carries the last value.
export function useDebounce<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(value);
    }, delayMs);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delayMs]);

  return debounced;
}
