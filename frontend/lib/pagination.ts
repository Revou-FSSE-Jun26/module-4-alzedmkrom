// Reads the `page` query value. Anything that is not a whole number from 1 up falls back to 1
// (BE-ERR-03 defaults). The backend rejects larger values, so this only protects the URL.
export function parsePage(raw: string | string[] | undefined): number {
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (value === undefined || !/^\d+$/.test(value)) {
    return 1;
  }
  const page = Number(value);
  return page >= 1 ? page : 1;
}

/** Builds a `?query` string for a link, keeping the other parameters. */
export function pageHref(
  basePath: string,
  params: Record<string, string>,
  page: number,
): string {
  const query = new URLSearchParams({ ...params, page: String(page) });
  return `${basePath}?${query.toString()}`;
}
