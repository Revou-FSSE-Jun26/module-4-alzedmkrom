import type { BoardRole } from "@/types/api";

// The only place that maps `my_role` to UI flags (FE-ROLE-01). The server decides every
// action (BE-AZ-02). These flags only decide what to show.
export interface RoleFlags {
  role: BoardRole;
  /** Member or Admin: create and edit columns and cards, comment, and drag cards. */
  canWrite: boolean;
  /** Admin: manage the board, its members, analytics, and any delete. */
  canManage: boolean;
  /** Logged in with no membership on this board (read-only). */
  isGuest: boolean;
  /** No token at all. */
  isAnonymous: boolean;
}

export function rolesFor(role: BoardRole): RoleFlags {
  return {
    role,
    canWrite: role === "member" || role === "admin",
    canManage: role === "admin",
    isGuest: role === "guest",
    isAnonymous: role === "anonymous",
  };
}
