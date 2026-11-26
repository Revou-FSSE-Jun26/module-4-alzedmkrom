import { ApiError } from "@/lib/errors";

/**
 * Maps the `details` of a 422 onto the form fields (FE-FRM-02).
 * `fields` lists the field names the form owns. Messages for other keys are returned as
 * `unmatched`, so the caller can show them in a toast.
 */
export function mapFieldDetails<K extends string>(
  error: ApiError,
  fields: readonly K[],
): { mapped: Partial<Record<K, string>>; unmatched: string[] } {
  const mapped: Partial<Record<K, string>> = {};
  const unmatched: string[] = [];
  const details = error.details ?? {};
  for (const [key, messages] of Object.entries(details)) {
    const first = messages[0];
    if (first === undefined) {
      continue;
    }
    if ((fields as readonly string[]).includes(key)) {
      mapped[key as K] = first;
    } else {
      unmatched.push(first);
    }
  }
  return { mapped, unmatched };
}
