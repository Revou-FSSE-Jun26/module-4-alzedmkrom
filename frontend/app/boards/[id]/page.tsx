import { notFound } from "next/navigation";
import { BoardView } from "@/components/board/BoardView";
import { ApiError } from "@/lib/errors";
import { serverApi } from "@/lib/serverApi";
import { rolesFor } from "@/lib/roles";
import type { BoardDetail, Items, Member } from "@/types/api";

// Board page (FE-PAGE-03). Anonymous visitors and Guests read public boards through the optional-auth
// fetch. The members list is requested only for Members and Admins (FE-PAGE-07), so a Guest never
// sees a 403 for a page they can read.
export default async function BoardPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const boardPath = `/api/boards/${encodeURIComponent(id)}`;

  let board: BoardDetail;
  try {
    board = await serverApi.getOptional<BoardDetail>(boardPath);
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 404) {
      notFound();
    }
    throw error;
  }

  let members: Member[] = [];
  if (rolesFor(board.my_role).canWrite) {
    try {
      members = (await serverApi.get<Items<Member>>(`${boardPath}/members`)).items;
    } catch (error) {
      if (!(error instanceof ApiError && error.statusCode === 403)) {
        throw error;
      }
    }
  }

  return <BoardView initialBoard={board} members={members} />;
}
