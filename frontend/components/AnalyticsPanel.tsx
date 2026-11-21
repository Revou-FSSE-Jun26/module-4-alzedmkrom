import type { Analytics } from '@/lib/types';
import { barPercentages, sortByActionsDesc } from '@/lib/collections';
import { BaseBadge } from '@/components/shared/BaseBadge';

export interface AnalyticsPanelProps {
  cardsPerColumn: Analytics['cards_per_column'];
  completedThisWeek: Analytics['completed_this_week'];
  memberActivity: Analytics['member_activity'];
}

export function AnalyticsPanel({ cardsPerColumn, completedThisWeek, memberActivity }: AnalyticsPanelProps) {
  const percentages = barPercentages(cardsPerColumn.map((column) => column.card_count));
  const members = sortByActionsDesc(memberActivity);

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="analytics-cards-heading">
        <h2 id="analytics-cards-heading" className="mb-3 text-lg font-semibold">Cards per column</h2>
        {cardsPerColumn.length === 0 ? (
          <p>This board has no columns</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {cardsPerColumn.map((column, index) => (
              <li key={column.column_id}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{column.title}</span>
                  <span>{column.card_count}</span>
                </div>
                <div className="h-3 w-full rounded bg-gray-100">
                  <div
                    role="img"
                    aria-label={`${column.title}: ${column.card_count}`}
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
        <h2 id="analytics-completed-heading" className="mb-3 text-lg font-semibold">Completed this week</h2>
        <BaseBadge color="green">{completedThisWeek}</BaseBadge>
      </section>

      <section aria-labelledby="analytics-members-heading">
        <h2 id="analytics-members-heading" className="mb-3 text-lg font-semibold">Member activity</h2>
        <ul className="flex flex-col gap-2">
          {members.map((member) => (
            <li key={member.user_id} className="flex justify-between text-sm">
              <span>{member.name}</span>
              <span>{member.actions}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
