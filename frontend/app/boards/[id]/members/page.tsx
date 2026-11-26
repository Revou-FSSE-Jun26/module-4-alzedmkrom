import { notFound, redirect } from "next/navigation";
import { MemberList } from "@/components/board/MemberList";
import { NotMemberMessage } from "@/components/NotMemberMessage";
import { ApiError } from "@/lib/errors";
import { serverApi } from "@/lib/serverApi";
import { getServerSession } from "@/lib/serverSession";
import { loginPath } from "@/lib/session";
import type { Items, Member } from "@/types/api";

// Board members (FE-PAGE-07). Members and Admins can view the list. Admins manage it.
// serverApi.get redirects on 401 by throwing, so the catch below handles only 404 and 403.
export default async function BoardMembersPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const membersPath = `/api/boards/${encodeURIComponent(id)}/members`;
  const session = await getServerSession();
  if (session.user === null) {
    redirect(loginPath({ next: `/boards/${id}/members` }));
  }

  let members: Member[];
  try {
    members = (await serverApi.get<Items<Member>>(membersPath)).items;
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 404) {
      notFound();
    }
    if (error instanceof ApiError && error.statusCode === 403) {
      return <NotMemberMessage />;
    }
    throw error;
  }

  const currentUserId = session.user.id;
  const isAdmin = members.find((member) => member.user_id === currentUserId)?.role === "admin";

  return (
    <MemberList
      boardId={id}
      initialMembers={members}
      currentUserId={currentUserId}
      isAdmin={isAdmin}
    />
  );
}
