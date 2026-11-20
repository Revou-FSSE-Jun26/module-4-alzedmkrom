/**
 * Order_Helper: pure functions that compute the floating-point `order` of a
 * card or column after a drop. No React or DOM imports.
 */

/**
 * Returns the `order` for a slot between two neighbours.
 *
 * @param above `order` of the item before the slot, or `null` at the top.
 * @param below `order` of the item after the slot, or `null` at the bottom.
 */
export function orderBetween(above: number | null, below: number | null): number {
  if (above !== null && below !== null) {
    return (above + below) / 2;
  }
  if (above !== null) {
    return above + 1.0;
  }
  if (below !== null) {
    return below / 2;
  }
  return 1.0;
}

/**
 * Returns the `order` for inserting at `index` into a list whose items already
 * have the given orders.
 *
 * @param sortedOthers `order` values of the target's items, without the dragged
 *   item, sorted ascending.
 * @param index insertion index from 0 to `sortedOthers.length` (inclusive).
 * @throws RangeError when `index` is not an integer in that range.
 */
export function orderForIndex(sortedOthers: readonly number[], index: number): number {
  if (!Number.isInteger(index) || index < 0 || index > sortedOthers.length) {
    throw new RangeError(
      `index must be an integer from 0 to ${sortedOthers.length}, got ${index}`,
    );
  }
  const above = index > 0 ? sortedOthers[index - 1] : null;
  const below = index < sortedOthers.length ? sortedOthers[index] : null;
  return orderBetween(above, below);
}

/**
 * Returns the index of the first midpoint greater than `pointer`, or
 * `midpoints.length` when none is greater.
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
