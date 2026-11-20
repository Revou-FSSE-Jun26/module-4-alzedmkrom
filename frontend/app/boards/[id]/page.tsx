import { notFound } from "next/navigation";
import { BoardView } from "@/components/BoardView";
import { NotMemberMessage } from "@/components/NotMemberMessage";
import { ApiError } from "@/lib/errors";
import { serverApi } from "@/lib/serverApi";
import type { BoardDetail, Member } from "@/lib/types";

// Board page (Requirements 10.1, 10.5, 10.6, 10.13, 13.12, 23.1, 23.3). A Server Component
// that loads the board and its members, then hands them to the interactive BoardView.
// serverApi.get redirects on 401 by throwing, so the catch below rethrows anything that
// is not a 404 or 403 ApiError. Unhandled errors reach app/error.tsx.
export default async function BoardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const boardPath = `/api/boards/${encodeURIComponent(id)}`;

  // Both requests start before either one is awaited.
  const boardRequest = serverApi.get<BoardDetail>(boardPath);
  const membersRequest = serverApi.get<Member[]>(`${boardPath}/members`);

  let board: BoardDetail;
  let members: Member[];
  try {
    [board, members] = await Promise.all([boardRequest, membersRequest]);
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 404) {
      notFound();
    }
    if (error instanceof ApiError && error.statusCode === 403) {
      return <NotMemberMessage />;
    }
    throw error;
  }

  return <BoardView initialBoard={board} members={members} />;
}
