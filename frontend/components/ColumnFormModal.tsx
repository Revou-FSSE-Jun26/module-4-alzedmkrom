"use client";

import { useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { FormField } from "@/components/shared/FormField";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import type { Column } from "@/lib/types";
import { validateRequiredText } from "@/lib/validation";

const COLUMN_TITLE_MAX = 255;

export interface ColumnFormModalProps {
  mode: "create" | "rename";
  open: boolean;
  boardId: string;
  column?: Column;
  onClose: () => void;
  // Receives the column returned by the API so the parent can dispatch it.
  onSaved: (column: Column) => void;
}

// Creates a column on a board, or renames an existing one (Requirements 11.1 to 11.5, 11.11).
export function ColumnFormModal({
  mode,
  open,
  boardId,
  column,
  onClose,
  onSaved,
}: ColumnFormModalProps) {
  const api = useApi();
  const handleError = useErrorHandler();

  const initialTitle = mode === "rename" && column ? column.title : "";
  const [title, setTitle] = useState(initialTitle);
  const [titleError, setTitleError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [seen, setSeen] = useState({ open, initialTitle });

  // The modal stays mounted between openings, so each opening restarts from the
  // initial values. This runs during render, not in an effect, to avoid a cascading render.
  if (seen.open !== open || seen.initialTitle !== initialTitle) {
    setSeen({ open, initialTitle });
    if (open) {
      setTitle(initialTitle);
      setTitleError(null);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }

    const validationError = validateRequiredText("Title", title, COLUMN_TITLE_MAX);
    setTitleError(validationError);
    if (validationError !== null) {
      return;
    }

    const trimmed = title.trim();
    setPending(true);
    try {
      const saved =
        mode === "create"
          ? await api.post<Column>(`/api/boards/${boardId}/columns`, { title: trimmed })
          : await api.patch<Column>(`/api/columns/${column?.id ?? ""}`, { title: trimmed });
      setPending(false);
      onSaved(saved);
      onClose();
    } catch (caught) {
      // The modal stays open with the typed title, and submit is enabled again.
      setPending(false);
      handleError(caught);
    }
  }

  return (
    <BaseModal open={open} title={mode === "create" ? "Add column" : "Rename column"} onClose={onClose}>
      <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
        <FormField label="Title" error={titleError}>
          {(control) => (
            <input
              {...control}
              type="text"
              name="title"
              autoComplete="off"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 aria-[invalid=true]:border-red-600"
            />
          )}
        </FormField>

        <div className="flex justify-end gap-2">
          <BaseButton variant="secondary" onClick={onClose}>
            Cancel
          </BaseButton>
          <BaseButton type="submit" loading={pending}>
            {mode === "create" ? "Create" : "Save"}
          </BaseButton>
        </div>
      </form>
    </BaseModal>
  );
}
