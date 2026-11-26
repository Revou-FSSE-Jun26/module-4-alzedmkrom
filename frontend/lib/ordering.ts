// Position calculation for drag and drop (FE-DND-02). Pure functions, no React or DOM imports.
// The constants and formulas copy backend.md BE-ORD-01. The server renumbers a container
// when neighbours get closer than MIN_GAP (BE-ORD-02).

/** BE-ORD-01: step used when a new item goes to an empty or end position. */
export const ORDER_STEP = 1024.0;

/** BE-ORD-01: a gap below this triggers a server rebalance (BE-ORD-02). */
export const MIN_GAP = 1e-6;

/**
 * BE-ORD-01 formulas. `previous` and `next` are the `order` values of the neighbours
 * of the slot, excluding the dragged item. Pass `null` for a missing neighbour.
 *
 * - both neighbours: (previous + next) / 2
 * - only `next` (start of the container): next / 2
 * - only `previous` (end of the container): previous + ORDER_STEP
 * - empty container: ORDER_STEP
 */
export function computeOrder(previous: number | null, next: number | null): number {
  if (previous !== null && next !== null) {
    return (previous + next) / 2;
  }
  if (next !== null) {
    return next / 2;
  }
  if (previous !== null) {
    return previous + ORDER_STEP;
  }
  return ORDER_STEP;
}

/**
 * Returns the `order` for inserting at `index` into a list whose items already have the
 * given orders (sorted ascending, dragged item excluded).
 *
 * @throws RangeError when `index` is not an integer from 0 to `sortedOthers.length`.
 */
export function orderForIndex(sortedOthers: readonly number[], index: number): number {
  if (!Number.isInteger(index) || index < 0 || index > sortedOthers.length) {
    throw new RangeError(
      `index must be an integer from 0 to ${sortedOthers.length}, got ${index}`,
    );
  }
  const previous = index > 0 ? sortedOthers[index - 1] : null;
  const next = index < sortedOthers.length ? sortedOthers[index] : null;
  return computeOrder(previous, next);
}

/**
 * Returns the index of the first midpoint greater than `pointer`, or `midpoints.length`
 * when none is greater.
 *
 * @param midpoints vertical (or horizontal) midpoints, sorted ascending.
 * @param pointer pointer coordinate at the drop.
 */
export function dropIndex(midpoints: readonly number[], pointer: number): number {
  let low = 0;
  let high = midpoints.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (midpoints[mid] > pointer) {
      high = mid;
    } else {
      low = mid + 1;
    }
  }
  return low;
}
