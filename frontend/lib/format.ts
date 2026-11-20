// Display formatting helpers.

export function formatUnreadCount(n: number): string | null {
  if (n === 0) {
    return null;
  }
  if (n > 99) {
    return "99+";
  }
  return String(n);
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString();
}
