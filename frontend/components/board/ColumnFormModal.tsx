"use client";

import { useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { FormAlert } from "@/components/shared/FormAlert";
import { FormField } from "@/components/shared/FormField";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import { mapFieldDetails } from "@/lib/formErrors";
import { LIMITS, validateRequiredText } from "@/lib/validation";
import type { Column } from "@/types/api";

export interface ColumnFormModalProps {
  mode: "create" | "rename";
  open: boolean;
  boardId: string;
  column?: Column;
  onClose: () => void;
  /** Receives the column returned by the API so the parent can dispatch it. */
  onSaved: (column: Column) => void;
}

// Creates a column on a board, or renames an existing one (FE-PAGE-07).
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
  const initialName = mode === "rename" && column ? column.name : "";
  const [name, setName] = useState(initialName);
  const [nameError, setNameError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [seen, setSeen] = useState({ open, initialName });

  // The modal stays mounted between openings, so each opening restarts from the initial values.
  // This runs during render, not in an effect, to avoid a cascading render.
  if (seen.open !== open || seen.initialName !== initialName) {
    setSeen({ open, initialName });
    if (open) {
      setName(initialName);
      setNameError(null);
      setFormError(null);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }
    const validationError = validateRequiredText("Name", name, LIMITS.columnName);
    setNameError(validationError);
    setFormError(null);
    if (validationError !== null) {
      return;
    }
    const trimmed = name.trim();
    setPending(true);
    try {
      const saved =
        mode === "create"
          ? await api.post<Column>(`/api/boards/${boardId}/columns`, { name: trimmed })
          : await api.patch<Column>(`/api/columns/${column?.id ?? ""}`, { name: trimmed });
      setPending(false);
      onSaved(saved);
      onClose();
    } catch (caught) {
      // The modal stays open with the typed name, and submit is enabled again (FE-FRM-03).
      setPending(false);
      if (caught instanceof ApiError && caught.statusCode === 422 && caught.details !== null) {
        const { mapped, unmatched } = mapFieldDetails(caught, ["name"] as const);
        setNameError(mapped.name ?? null);
        setFormError(unmatched.length > 0 ? unmatched.join(" ") : null);
        return;
      }
      handleError(caught);
    }
  }

  return (
    <BaseModal
      open={open}
      title={mode === "create" ? "Add column" : "Rename column"}
      onClose={onClose}
      dismissDisabled={pending}
    >
      <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
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
