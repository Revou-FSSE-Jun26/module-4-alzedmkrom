"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AddMemberModal } from "@/components/AddMemberModal";
import { BaseBadge, type BadgeColor } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { ConfirmModal } from "@/components/shared/ConfirmModal";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { formatDate } from "@/lib/format";
import type { Member, Role } from "@/lib/types";

const SELECT_CLASSES =
  "rounded-md border border-gray-300 px-2 py-1 text-sm text-gray-900 disabled:opacity-60";

const ROLE_BADGE_COLORS: Record<Role, BadgeColor> = {
  admin: "blue",
  member: "gray",
};

export interface MemberListProps {
  boardId: string;
  initialMembers: Member[];
  currentUserId: string;
  isAdmin: boolean;
}

// Board members table with role, removal and leave actions (Requirements 19.1, 19.5 to 19.10).
export function MemberList({ boardId, initialMembers, currentUserId, isAdmin }: MemberListProps) {
  const api = useApi();
  const handleError = useErrorHandler();
  const router = useRouter();

  const [members, setMembers] = useState<Member[]>(initialMembers);
  const [rolePendingId, setRolePendingId] = useState<string | null>(null);
  const [removing, setRemoving] = useState<Member | null>(null);
  const [removePending, setRemovePending] = useState(false);

  const membersPath = `/api/boards/${boardId}/members`;
  const removingSelf = removing !== null && removing.user_id === currentUserId;

  // On failure the state keeps the previous role, so the controlled select shows that role again.
  async function handleRoleChange(member: Member, role: Role) {
    setRolePendingId(member.user_id);
    try {
      const updated = await api.patch<Member>(`${membersPath}/${member.user_id}`, { role });
      setMembers((current) =>
        current.map((row) => (row.user_id === member.user_id ? { ...row, role: updated.role } : row)),
      );
    } catch (caught) {
      handleError(caught);
    } finally {
      setRolePendingId(null);
    }
  }

  async function handleRemoveConfirmed() {
    if (removing === null || removePending) {
      return;
    }
    const target = removing;
    setRemovePending(true);
    try {
      await api.delete(`${membersPath}/${target.user_id}`);
      if (target.user_id === currentUserId) {
        router.push("/");
        return;
      }
      setMembers((current) => current.filter((row) => row.user_id !== target.user_id));
    } catch (caught) {
      handleError(caught);
    } finally {
      setRemovePending(false);
      setRemoving(null);
    }
  }

  function handleMemberAdded(member: Member) {
    setMembers((current) => [...current, member]);
  }

  return (
    <section className="flex flex-col gap-4">
      {isAdmin ? (
        <div className="flex justify-end">
          <AddMemberModal boardId={boardId} onAdded={handleMemberAdded} />
        </div>
      ) : null}

      <ul className="divide-y divide-gray-200 rounded-md border border-gray-200 bg-white">
        {members.map((member) => {
          const isSelf = member.user_id === currentUserId;

          return (
            <li key={member.user_id} className="flex flex-wrap items-center gap-4 px-4 py-3">
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-sm font-medium text-gray-900">{member.name}</span>
                <span className="truncate text-sm text-gray-600">{member.email}</span>
              </div>

              <BaseBadge color={ROLE_BADGE_COLORS[member.role]}>{member.role}</BaseBadge>

              <time dateTime={member.created_at} suppressHydrationWarning className="text-sm text-gray-600">
                {formatDate(member.created_at)}
              </time>

              {isAdmin ? (
                <div className="flex items-center gap-2">
                  <select
                    aria-label={`Role of ${member.name}`}
                    value={member.role}
                    disabled={rolePendingId === member.user_id}
                    onChange={(event) => void handleRoleChange(member, event.target.value as Role)}
                    className={SELECT_CLASSES}
                  >
                    <option value="member">member</option>
                    <option value="admin">admin</option>
                  </select>
                  <BaseButton variant="secondary" onClick={() => setRemoving(member)}>
                    Remove
                  </BaseButton>
                </div>
              ) : null}

              {!isAdmin && isSelf ? (
                <BaseButton variant="secondary" onClick={() => setRemoving(member)}>
                  Leave board
                </BaseButton>
              ) : null}
            </li>
          );
        })}
      </ul>

      <ConfirmModal
        open={removing !== null}
        title={removingSelf ? "Leave board" : "Remove member"}
        message={
          removing === null
            ? ""
            : removingSelf
              ? "Leave this board? You will lose access to it."
              : `Remove ${removing.name} from this board?`
        }
        confirmLabel={removingSelf ? "Leave" : "Remove"}
        pending={removePending}
        onConfirm={() => void handleRemoveConfirmed()}
        onCancel={() => setRemoving(null)}
      />
    </section>
  );
}
