import { OpenBoardButton } from "@/components/OpenBoardButton";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { serverApi } from "@/lib/serverApi";
import type { MyTasksGroup } from "@/lib/types";

// My Tasks (Requirements 8.9, 16.1 to 16.7, 23.1). A Server Component: the assigned cards are
// fetched on the server, and only OpenBoardButton ships client code. Failures other than 401
// are not caught here, so they reach app/error.tsx.
export default async function MyTasksPage() {
  const groups = await serverApi.get<MyTasksGroup[]>("/api/cards?assignee=me");

  return (
    <section className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-gray-900">My tasks</h1>
      {groups.length === 0 ? (
        <p className="text-sm text-gray-600">No cards are assigned to you</p>
      ) : (
        groups.map((group) => (
          <section key={group.board_id} className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold text-gray-900">{group.board_name}</h2>
            <ul className="flex flex-col gap-2">
              {group.cards.map((card) => (
                <li
                  key={card.id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-gray-200 bg-white px-4 py-3"
                >
                  <span className="font-medium text-gray-900">{card.title}</span>
                  <div className="flex items-center gap-3">
                    <BaseBadge color={card.completed_at !== null ? "green" : "gray"}>
                      {card.completed_at !== null ? "Completed" : "Open"}
                    </BaseBadge>
                    <OpenBoardButton boardId={group.board_id} />
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </section>
  );
}
