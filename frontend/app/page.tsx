import Link from "next/link";
import { CreateBoardModal } from "@/components/CreateBoardModal";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { serverApi } from "@/lib/serverApi";
import type { Board } from "@/lib/types";

// Dashboard (Requirements 9.1, 9.2, 9.3, 9.7, 23.1). A Server Component: the board list is
// fetched on the server, and only CreateBoardModal ships client code.
export default async function DashboardPage() {
  const boards = await serverApi.get<Board[]>("/api/boards");

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-gray-900">Your boards</h1>
        <CreateBoardModal />
      </div>

      {boards.length === 0 ? (
        <p className="text-sm text-gray-600">You have no boards yet</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {boards.map((board) => (
            <li key={board.id}>
              <Link
                href={"/boards/" + board.id}
                className="flex items-center justify-between gap-4 rounded-md border border-gray-200 bg-white px-4 py-3 text-gray-900 hover:border-gray-400"
              >
                <span className="font-medium">{board.name}</span>
                <BaseBadge color={board.role === "admin" ? "blue" : "gray"}>{board.role}</BaseBadge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
