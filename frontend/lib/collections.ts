// Pure sorting and bar-scaling helpers. Every sort returns a new array and
// leaves its input untouched. Array.prototype.sort is stable (ES2019+), so
// items with equal keys keep their input order.

export function sortByOrder<T extends { order: number }>(items: readonly T[]): T[] {
  return [...items].sort((a, b) => a.order - b.order);
}

export function sortByCreatedAt<T extends { created_at: string }>(
  items: readonly T[],
  dir: "asc" | "desc",
): T[] {
  const sign = dir === "asc" ? 1 : -1;
  return [...items].sort(
    (a, b) => sign * (Date.parse(a.created_at) - Date.parse(b.created_at)),
  );
}

export function sortByActionsDesc<T extends { actions: number }>(items: readonly T[]): T[] {
  return [...items].sort((a, b) => b.actions - a.actions);
}

export function barPercentages(counts: readonly number[]): number[] {
  const max = counts.reduce((acc, count) => (count > acc ? count : acc), 0);
  if (max === 0) {
    return counts.map(() => 0);
  }
  return counts.map((count) => (count / max) * 100);
}
