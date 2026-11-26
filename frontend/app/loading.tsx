import { PageSkeleton } from "@/components/shared/PageSkeleton";

// Dashboard loading state (FE-UX-01). Also shown while other root-level routes load.
export default function Loading() {
  return <PageSkeleton rows={4} label="Loading boards" />;
}
