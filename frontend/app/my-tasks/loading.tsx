import { PageSkeleton } from "@/components/shared/PageSkeleton";

// My tasks loading state (FE-UX-01, FE-PAGE-05).
export default function MyTasksLoading() {
  return <PageSkeleton rows={3} label="Loading your tasks" />;
}
