// Loading placeholder for route loading.tsx files (FE-UX-01). Pure markup, so it renders on the server.
interface PageSkeletonProps {
  /** Number of placeholder rows or cards to draw. */
  rows?: number;
  /** Accessible name announced while the route loads. */
  label: string;
}

export function PageSkeleton({ rows = 3, label }: PageSkeletonProps) {
  return (
    <div role="status" aria-label={label} className="flex flex-col gap-6 p-4 sm:p-6">
      <span className="sr-only">{label}</span>
      <div aria-hidden="true" className="h-8 w-48 animate-pulse rounded-md bg-gray-200" />
      <div aria-hidden="true" className="flex flex-col gap-3">
        {Array.from({ length: rows }, (_, index) => (
          <div key={index} className="h-16 animate-pulse rounded-md border border-gray-200 bg-gray-100" />
        ))}
      </div>
    </div>
  );
}
