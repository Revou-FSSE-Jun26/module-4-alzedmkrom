import Link from "next/link";
import { notFound } from "next/navigation";
import { AnalyticsPanel } from "@/components/board/AnalyticsPanel";
import { ApiError } from "@/lib/errors";
import { serverApi } from "@/lib/serverApi";
import type { Analytics } from "@/types/api";

// Board analytics page (Requirements 20.1, 20.5, 20.7, 23.1). A Server Component that loads
// the analytics once. serverApi.get redirects on 401 by throwing, so the catch below handles
// only the 404 and 403 ApiErrors and rethrows everything else. A 403 renders the admin-only
// message with no chart, count or member list. A 404 calls notFound().
export default async function BoardAnalyticsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let analytics: Analytics;
  try {
    analytics = await serverApi.get<Analytics>(`/api/boards/${encodeURIComponent(id)}/analytics`);
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 404) {
      notFound();
    }
    if (error instanceof ApiError && error.statusCode === 403) {
      return (
        <div className="flex flex-col gap-3">
          <p>Analytics are available to board administrators</p>
          <Link href={`/boards/${encodeURIComponent(id)}`} className="text-blue-600 underline">
            Back to the board
          </Link>
        </div>
      );
    }
    throw error;
  }

  return (
    <AnalyticsPanel
      cardsPerColumn={analytics.cards_per_column}
      completedThisWeek={analytics.completed_this_week}
      memberActivity={analytics.member_activity}
    />
  );
}
