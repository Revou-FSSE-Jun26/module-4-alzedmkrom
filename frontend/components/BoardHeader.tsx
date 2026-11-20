"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { ConfirmModal } from "@/components/shared/ConfirmModal";
import { FormField } from "@/components/shared/FormField";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { success as showSuccessToast } from "@/lib/toast";
import type { Board, Role } from "@/lib/types";
import { validateRequiredText } from "@/lib/validation";

const BOARD_NAME_MAX = 255;

export interface BoardHeaderProps {
  board: { id: string; name: string; role: Role };
  onRenamed(name: string): void;
}

// Board title, role badge and board-level actions (Requirements 10.7 to 10.12).
// Only a board admin sees the rename and delete buttons and the analytics link.
export function BoardHeader({ board, onRenamed }: BoardHeaderProps) {
  const router = useRouter();
  const api = useApi();
  const handleError = useErrorHandler();
  const isAdmin = board.role === "admin";

  const [renameOpen, setRenameOpen] = useState(false);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [renamePending, setRenamePending] = useState(false);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePending, setDeletePending] = useState(false);

  function openRename() {
    setName(board.name);
    setNameError(null);
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
    const validationError = validateRequiredText("Name", name, BOARD_NAME_MAX);
    setNameError(validationError);
    if (validationError !== null) {
      return;
    }
    setRenamePending(true);
    try {
      const updated = await api.patch<Board>("/api/boards/" + board.id, { name: name.trim() });
      setRenamePending(false);
      onRenamed(updated.name);
      setRenameOpen(false);
      showSuccessToast("Board renamed.");
    } catch (caught) {
      setRenamePending(false);
      handleError(caught);
    }
  }

  async function handleDelete() {
    if (deletePending) {
      return;
    }
    setDeletePending(true);
    try {
      await api.delete<{ id: string }>("/api/boards/" + board.id);
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
      <BaseBadge color={isAdmin ? "blue" : "gray"}>{board.role}</BaseBadge>
      <Link
        href={"/boards/" + board.id + "/members"}
        className="text-sm font-medium text-blue-700 underline-offset-2 hover:underline"
      >
        Members
      </Link>
      {isAdmin ? (
        <>
          <Link
            href={"/boards/" + board.id + "/analytics"}
            className="text-sm font-medium text-blue-700 underline-offset-2 hover:underline"
          >
            Analytics
          </Link>
          <BaseButton variant="secondary" onClick={openRename}>
            Rename board
          </BaseButton>
          <BaseButton variant="destructive" onClick={() => setDeleteOpen(true)}>
            Delete board
          </BaseButton>
        </>
      ) : null}

      {isAdmin ? (
        <>
          <BaseModal open={renameOpen} title="Rename board" onClose={closeRename}>
            <form className="flex flex-col gap-4" noValidate onSubmit={handleRename}>
              <FormField label="Name" error={nameError}>
                {(control) => (
                  <input
                    {...control}
                    type="text"
                    name="name"
                    autoComplete="off"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 aria-[invalid=true]:border-red-600"
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
