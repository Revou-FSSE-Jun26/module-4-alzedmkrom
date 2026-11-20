"use client";

import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { useApi } from "@/hooks/useApi";
import { useDebounce } from "@/hooks/useDebounce";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import type { Card } from "@/lib/types";
import { LIMITS } from "@/lib/validation";

const SEARCH_DEBOUNCE_MS = 300;

// Keeps the first `max` code points of `value`. Counting code points, not UTF-16 units,
// matches the API limit (Requirement 15.1).
function truncateToCodePoints(value: string, max: number): string {
  const codePoints = [...value];
  return codePoints.length > max ? codePoints.slice(0, max).join("") : value;
}

export interface CardSearchProps {
  // Receives the ids of the matching cards, or null when no search is active.
  onResults(ids: ReadonlySet<string> | null): void;
}

// Search input for the open board (Requirements 15.1, 15.2, 15.3, 15.5, 15.7, 15.8).
export function CardSearch({ onResults }: CardSearchProps) {
  const api = useApi();
  const handleError = useErrorHandler();

  const [term, setTerm] = useState("");
  const debounced = useDebounce(term, SEARCH_DEBOUNCE_MS);
  const trimmed = debounced.trim();

  // Incremented for every search. A response applies only when its id is still the latest.
  const latestRequest = useRef(0);

  // The search effect reads the latest callbacks from this ref. Keeping them out of the
  // effect deps stops a new callback identity or a token refresh from resending the search.
  const latest = useRef({ api, onResults, handleError });
  useEffect(() => {
    latest.current = { api, onResults, handleError };
  });

  useEffect(() => {
    const current = latest.current;
    latestRequest.current += 1;
    const requestId = latestRequest.current;

    if (trimmed === "") {
      current.onResults(null);
      return;
    }

    current.api
      .get<Card[]>(`/api/cards?search=${encodeURIComponent(trimmed)}`)
      .then(
        (cards) => {
          if (requestId === latestRequest.current) {
            current.onResults(new Set(cards.map((card) => card.id)));
          }
        },
        (error: unknown) => {
          if (requestId === latestRequest.current) {
            current.handleError(error);
          }
        },
      );
  }, [trimmed]);

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    setTerm(truncateToCodePoints(event.target.value, LIMITS.search));
  }

  return (
    <input
      type="search"
      aria-label="Search cards"
      placeholder="Search cards"
      autoComplete="off"
      maxLength={200}
      value={term}
      onChange={handleChange}
      className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900"
    />
  );
}
