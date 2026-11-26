"use client";

import { useEffect, useState, type ChangeEvent } from "react";
import { useDebounce } from "@/hooks/useDebounce";
import { LIMITS } from "@/lib/validation";

const SEARCH_DEBOUNCE_MS = 300;

// Keeps the first `max` code points of `value`, matching the length the form allows.
function truncateToCodePoints(value: string, max: number): string {
  const codePoints = [...value];
  return codePoints.length > max ? codePoints.slice(0, max).join("") : value;
}

export interface CardSearchProps {
  /** Receives the trimmed search term after the input is idle. Empty means no filter. */
  onTermChange(term: string): void;
}

// Filters the cards already on the board. The backend has no card search endpoint, so the match
// runs in the browser over title and description (BoardView).
export function CardSearch({ onTermChange }: CardSearchProps) {
  const [term, setTerm] = useState("");
  const debounced = useDebounce(term, SEARCH_DEBOUNCE_MS);

  useEffect(() => {
    onTermChange(debounced.trim());
  }, [debounced, onTermChange]);

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor="card-search" className="text-base font-medium text-gray-800">
        Search cards
      </label>
      <input
        id="card-search"
        type="search"
        autoComplete="off"
        value={term}
        onChange={(event: ChangeEvent<HTMLInputElement>) =>
          setTerm(truncateToCodePoints(event.target.value, LIMITS.search))
        }
        className="rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900"
      />
    </div>
  );
}
