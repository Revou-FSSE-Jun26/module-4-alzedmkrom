import { PageSkeleton } from "@/components/shared/PageSkeleton";

// Board loading state (FE-UX-01, FE-PAGE-03).
export default function BoardLoading() {
  return <PageSkeleton rows={2} label="Loading board" />;
}
