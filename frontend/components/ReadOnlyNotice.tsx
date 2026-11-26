import Link from "next/link";
import type { BoardRole } from "@/types/api";

export interface ReadOnlyNoticeProps {
  role: BoardRole;
}

// The message that explains why a viewer cannot write (FE-ROLE-02). Each viewer gets a
// different next step.
export function ReadOnlyNotice({ role }: ReadOnlyNoticeProps) {
  if (role === "anonymous") {
    return (
      <p className="text-base text-gray-700">
        <Link href="/login" className="font-medium text-blue-700 underline">
          Log in to contribute
        </Link>
      </p>
    );
  }
  if (role === "guest") {
    return (
      <p className="text-base text-gray-700">
        You have read-only access. Ask a board admin to add you as a member.
      </p>
    );
  }
  return null;
}
