import { notFound, redirect } from "next/navigation";
import { MemberList } from "@/components/MemberList";
import { NotMemberMessage } from "@/components/NotMemberMessage";
import { ApiError } from "@/lib/errors";
import { serverApi } from "@/lib/serverApi";
import { getServerSession } from "@/lib/serverSession";
import type { Member } from "@/lib/types";

// Board members page (Requirements 19.1, 19.11, 23.1). A Server Component that loads the
// members and the cached session in parallel. serverApi.get redirects on 401 by throwing,
// so the catch below rethrows anything that is not a 404 or 403 ApiError. The notFound()
// and redirect() calls sit outside the try block.
export default async function BoardMembersPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const membersPath = `/api/boards/${encodeURIComponent(id)}/members`;

  let loaded: [Member[], Awaited<ReturnType<typeof getServerSession>>] | 404 | 403;
  try {
    loaded = await Promise.all([
      serverApi.get<Member[]>(membersPath),
      getServerSession(),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 404) {
      loaded = 404;
    } else if (error instanceof ApiError && error.statusCode === 403) {
      loaded = 403;
    } else {
      throw error;
    }
  }

  if (loaded === 404) {
    notFound();
  }
  if (loaded === 403) {
    return <NotMemberMessage />;
  }

  const [members, session] = loaded;
  if (session.user === null) {
    redirect("/login?reason=session-expired");
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
