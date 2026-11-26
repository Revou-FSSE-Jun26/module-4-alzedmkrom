import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { groupByBoard } from "@/lib/collections";
import { serverApi } from "@/lib/serverApi";
import { pageHref, parsePage } from "@/lib/pagination";
import type { AssignedCard, Paginated } from "@/types/api";

interface MyTasksPageProps {
  searchParams: Promise<{ page?: string | string[] }>;
}

// Assigned tasks (FE-PAGE-05). A protected page: proxy.ts and serverApi.get send Anonymous visitors to login.
export default async function MyTasksPage({ searchParams }: MyTasksPageProps) {
  const { page: rawPage } = await searchParams;
  const page = parsePage(rawPage);
  const query = new URLSearchParams({ assignee: "me", page: String(page), per_page: "20" });
  const data = await serverApi.get<Paginated<AssignedCard>>(`/api/cards?${query.toString()}`);
  const groups = groupByBoard(data.items);

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-gray-900">My tasks</h1>
      {groups.length === 0 ? (
        <p className="text-base text-gray-600">No cards are assigned to you.</p>
      ) : (
        groups.map((group) => (
          <section key={group.board_id} className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-gray-900">{group.board_name}</h2>
              <BaseButton variant="secondary" href={`/boards/${group.board_id}`}>
                Open board
              </BaseButton>
            </div>
            <ul className="flex flex-col gap-2">
              {group.cards.map((card) => (
                <li
                  key={card.id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-gray-200 bg-white px-4 py-3"
                >
                  <span className="text-base font-medium text-gray-900">{card.title}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-base text-gray-600">{card.column_name}</span>
                    <BaseBadge color={card.completed_at !== null ? "green" : "gray"}>
                      {card.completed_at !== null ? "Completed" : "Open"}
                    </BaseBadge>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}

      {data.pages > 1 ? (
        <nav aria-label="Pagination" className="flex items-center justify-between gap-4">
          {page > 1 ? (
            <BaseButton variant="secondary" href={pageHref("/my-tasks", {}, page - 1)}>
              Previous
            </BaseButton>
          ) : (
            <span />
          )}
          <span className="text-base text-gray-700">
            Page {page} of {data.pages}
          </span>
          {page < data.pages ? (
            <BaseButton variant="secondary" href={pageHref("/my-tasks", {}, page + 1)}>
              Next
            </BaseButton>
          ) : (
            <span />
          )}
        </nav>
      ) : null}
    </section>
  );
}
