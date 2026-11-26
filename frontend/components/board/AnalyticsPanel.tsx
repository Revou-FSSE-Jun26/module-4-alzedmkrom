import { BaseBadge } from "@/components/shared/BaseBadge";
import { barPercentages } from "@/lib/collections";
import type { Analytics } from "@/types/api";

export interface AnalyticsPanelProps {
  cardsPerColumn: Analytics["cards_per_column"];
  completedThisWeek: Analytics["completed_this_week"];
  memberActivity: Analytics["member_activity"];
}

// Admin-only analytics (BE-ANL-01). Counts come from the server, so this component only lays them out.
export function AnalyticsPanel({ cardsPerColumn, completedThisWeek, memberActivity }: AnalyticsPanelProps) {
  const percentages = barPercentages(cardsPerColumn.map((column) => column.total_cards));
  const members = [...memberActivity].sort(
    (a, b) => b.cards_created + b.comments_added + b.cards_assigned -
      (a.cards_created + a.comments_added + a.cards_assigned),
  );

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="analytics-cards-heading">
        <h2 id="analytics-cards-heading" className="mb-3 text-lg font-semibold text-gray-900">
          Cards per column
        </h2>
        {cardsPerColumn.length === 0 ? (
          <p className="text-base text-gray-600">This board has no columns</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {cardsPerColumn.map((column, index) => (
              <li key={column.column_id}>
                <div className="mb-1 flex justify-between text-base">
                  <span>{column.name}</span>
                  <span>{column.total_cards}</span>
                </div>
                <div className="h-3 w-full rounded bg-gray-100">
                  <div
                    role="img"
                    aria-label={`${column.name}: ${column.total_cards}`}
                    className="h-3 rounded bg-blue-500"
                    style={{ width: `${percentages[index]}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="analytics-completed-heading">
        <h2 id="analytics-completed-heading" className="mb-3 text-lg font-semibold text-gray-900">
          Completed this week
        </h2>
        <BaseBadge color="green">{completedThisWeek}</BaseBadge>
      </section>

      <section aria-labelledby="analytics-members-heading">
        <h2 id="analytics-members-heading" className="mb-3 text-lg font-semibold text-gray-900">
          Member activity
        </h2>
        {members.length === 0 ? (
          <p className="text-base text-gray-600">No member activity yet</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {members.map((member) => (
              <li key={member.user_id} className="flex flex-wrap justify-between gap-2 text-base">
                <span className="font-medium">{member.name}</span>
                <span className="text-gray-700">
                  Created {member.cards_created}, commented {member.comments_added}, assigned{" "}
                  {member.cards_assigned}, completed {member.assigned_cards_completed_this_week} this week
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
