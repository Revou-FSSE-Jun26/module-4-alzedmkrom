"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { ConfirmModal } from "@/components/shared/ConfirmModal";
import { FormAlert } from "@/components/shared/FormAlert";
import { FormField } from "@/components/shared/FormField";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import { mapFieldDetails } from "@/lib/formErrors";
import { rolesFor } from "@/lib/roles";
import { success as showSuccessToast } from "@/lib/toast";
import { LIMITS, validateRequiredText } from "@/lib/validation";
import type { Board, BoardRole } from "@/types/api";

const LINK_CLASSES = "text-base font-medium text-blue-700 underline-offset-2 hover:underline";

export interface BoardHeaderProps {
  board: { id: string; name: string; my_role: BoardRole };
  onRenamed(name: string): void;
}

const ROLE_LABELS: Record<BoardRole, string> = {
  anonymous: "Public viewer",
  guest: "Guest",
  member: "Member",
  admin: "Admin",
};

// Board title, role badge and board-level actions (FE-ROLE-01). Admin-only controls are the
// rename, delete, and analytics actions. Members see the member list.
export function BoardHeader({ board, onRenamed }: BoardHeaderProps) {
  const router = useRouter();
  const api = useApi();
  const handleError = useErrorHandler();
  const roles = rolesFor(board.my_role);
  const [renameOpen, setRenameOpen] = useState(false);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [renamePending, setRenamePending] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePending, setDeletePending] = useState(false);

  function openRename() {
    setName(board.name);
    setNameError(null);
    setFormError(null);
    setRenameOpen(true);
  }

  function closeRename() {
    setRenameOpen(false);
  }

  async function handleRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (renamePending) {
      return;
    }
    const validationError = validateRequiredText("Name", name, LIMITS.boardName);
    setNameError(validationError);
    setFormError(null);
    if (validationError !== null) {
      return;
    }
    setRenamePending(true);
    try {
      const updated = await api.patch<Board>(`/api/boards/${board.id}`, { name: name.trim() });
      setRenamePending(false);
      onRenamed(updated.name);
      setRenameOpen(false);
      showSuccessToast("Board renamed.");
    } catch (caught) {
      setRenamePending(false);
      if (caught instanceof ApiError && caught.statusCode === 422 && caught.details !== null) {
        const { mapped, unmatched } = mapFieldDetails(caught, ["name"] as const);
        setNameError(mapped.name ?? null);
        setFormError(unmatched.length > 0 ? unmatched.join(" ") : null);
        return;
      }
      handleError(caught);
    }
  }

  async function handleDelete() {
    if (deletePending) {
      return;
    }
    setDeletePending(true);
    try {
      await api.delete<void>(`/api/boards/${board.id}`);
      setDeletePending(false);
      setDeleteOpen(false);
      showSuccessToast("Board deleted.");
      router.push("/");
    } catch (caught) {
      setDeletePending(false);
      handleError(caught);
    }
  }

  return (
    <header className="flex flex-wrap items-center gap-3">
      <h1 className="min-w-0 break-words text-2xl font-semibold text-gray-900">{board.name}</h1>
      <BaseBadge color={roles.canManage ? "blue" : "gray"}>{ROLE_LABELS[board.my_role]}</BaseBadge>
      {roles.canWrite ? (
        <Link href={`/boards/${board.id}/members`} className={LINK_CLASSES}>
          Members
        </Link>
      ) : null}
      {roles.canManage ? (
        <>
          <Link href={`/boards/${board.id}/analytics`} className={LINK_CLASSES}>
            Analytics
          </Link>
          <BaseButton variant="secondary" onClick={openRename}>
            Rename board
          </BaseButton>
          <BaseButton variant="destructive" onClick={() => setDeleteOpen(true)}>
            Delete board
          </BaseButton>
          <BaseModal
            open={renameOpen}
            title="Rename board"
            onClose={closeRename}
            dismissDisabled={renamePending}
          >
            <form className="flex flex-col gap-4" noValidate onSubmit={handleRename}>
              <FormAlert message={formError} />
              <FormField label="Name" error={nameError}>
                {(control) => (
                  <input
                    {...control}
                    type="text"
                    name="name"
                    autoComplete="off"
                    value={name}
                    onChange={(event) => {
                      setName(event.target.value);
                      setNameError(null);
                    }}
                    className="rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900 aria-[invalid=true]:border-red-600"
                  />
                )}
              </FormField>
              <div className="flex justify-end gap-2">
                <BaseButton variant="secondary" onClick={closeRename}>
                  Cancel
                </BaseButton>
                <BaseButton type="submit" loading={renamePending}>
                  Save
                </BaseButton>
              </div>
            </form>
          </BaseModal>
          <ConfirmModal
            open={deleteOpen}
            title="Delete board"
            message={`Delete "${board.name}" and all its columns and cards? This cannot be undone.`}
            confirmLabel="Delete"
            pending={deletePending}
            onConfirm={() => void handleDelete()}
            onCancel={() => setDeleteOpen(false)}
          />
        </>
      ) : null}
    </header>
  );
}
