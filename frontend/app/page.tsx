import Link from "next/link";
import { CreateBoardModal } from "@/components/CreateBoardModal";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { serverApi } from "@/lib/serverApi";
import { getServerSession } from "@/lib/serverSession";
import { pageHref, parsePage } from "@/lib/pagination";
import type { Board, BoardRole, Paginated } from "@/types/api";

const ROLE_LABELS: Record<BoardRole, string> = {
  anonymous: "Public",
  guest: "Guest",
  member: "Member",
  admin: "Admin",
};

interface DashboardPageProps {
  searchParams: Promise<{ scope?: string | string[]; page?: string | string[] }>;
}

// Dashboard (FE-PAGE-02). The scope and page come from the URL, so links and refreshes work.
// Anonymous visitors always see public boards. Signed-in users default to their own boards.
export default async function DashboardPage({ searchParams }: DashboardPageProps) {
  const { scope: rawScope, page: rawPage } = await searchParams;
  const { user } = await getServerSession();
  const requested = Array.isArray(rawScope) ? rawScope[0] : rawScope;
  const scope = user === null || requested === "public" ? "public" : "mine";
  const page = parsePage(rawPage);

  const query = new URLSearchParams({ scope, page: String(page), per_page: "20" });
  const data = await serverApi.getOptional<Paginated<Board>>(`/api/boards?${query.toString()}`);
  const basePath = "/";
  const baseParams = { scope };

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-gray-900">Boards</h1>
        {user !== null ? <CreateBoardModal /> : null}
      </div>

      {user !== null ? (
        <nav aria-label="Board scope" className="flex flex-wrap gap-2">
          <Link
            href="/?scope=mine"
            aria-current={scope === "mine" ? "page" : undefined}
            className="rounded-md px-3 py-2 text-base font-medium text-blue-700 underline-offset-2 hover:underline"
          >
            My boards
          </Link>
          <Link
            href="/?scope=public"
            aria-current={scope === "public" ? "page" : undefined}
            className="rounded-md px-3 py-2 text-base font-medium text-blue-700 underline-offset-2 hover:underline"
          >
            Public boards
          </Link>
        </nav>
      ) : null}

      {data.items.length === 0 ? (
        <p className="text-base text-gray-600">
          {scope === "mine" ? "You have no boards yet." : "No public boards yet."}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {data.items.map((board) => (
            <li key={board.id}>
              <Link
                href={`/boards/${board.id}`}
                className="flex items-center justify-between gap-4 rounded-md border border-gray-200 bg-white px-4 py-3 text-gray-900 hover:border-gray-400"
              >
                <span className="text-lg font-medium">{board.name}</span>
                <span className="flex items-center gap-2">
                  {board.is_public ? null : <BaseBadge color="gray">Private</BaseBadge>}
                  <BaseBadge color={board.my_role === "admin" ? "blue" : "gray"}>
                    {ROLE_LABELS[board.my_role]}
                  </BaseBadge>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {data.pages > 1 ? (
        <nav aria-label="Pagination" className="flex items-center justify-between gap-4">
          {page > 1 ? (
            <BaseButton variant="secondary" href={pageHref(basePath, baseParams, page - 1)}>
              Previous
            </BaseButton>
          ) : (
            <span />
          )}
          <span className="text-base text-gray-700">
            Page {page} of {data.pages}
          </span>
          {page < data.pages ? (
            <BaseButton variant="secondary" href={pageHref(basePath, baseParams, page + 1)}>
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
