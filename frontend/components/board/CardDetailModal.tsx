"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { ConfirmModal } from "@/components/shared/ConfirmModal";
import { FormAlert } from "@/components/shared/FormAlert";
import { FormField } from "@/components/shared/FormField";
import { CommentList } from "@/components/board/CommentList";
import { ReadOnlyNotice } from "@/components/ReadOnlyNotice";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import type { DragAndDrop } from "@/hooks/useDragAndDrop";
import type { BoardColumn } from "@/lib/boardState";
import { sortByOrder } from "@/lib/collections";
import { ApiError } from "@/lib/errors";
import { mapFieldDetails } from "@/lib/formErrors";
import { rolesFor } from "@/lib/roles";
import { success as showSuccessToast } from "@/lib/toast";
import {
  changedCardFields,
  LIMITS,
  validateOptionalText,
  validateRequiredText,
  type CardField,
  type CardFieldValues,
} from "@/lib/validation";
import type { BoardRole, Card, Member } from "@/types/api";

const INPUT_CLASSES =
  "rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900 aria-[invalid=true]:border-red-600";

type FormField_ = "title" | "description";

export interface CardDetailModalProps {
  card: Card;
  /** The column that holds the card. The Column select shows this value. */
  columnId: string;
  columns: readonly BoardColumn[];
  members: readonly Member[];
  role: BoardRole;
  dnd: DragAndDrop;
  onClose: () => void;
  /** Receives the card returned by PATCH /api/cards/<id>. */
  onSaved: (card: Card) => void;
  onDeleted: (cardId: string) => void;
}

// Edit form, column move, delete and comments for one card (FE-PAGE-04, FE-DND-05).
// Writes show only for Members and Admins. Delete is Admin, or the Member who created the card
// (BE-AZ-04). The server still decides every action.
export function CardDetailModal({
  card,
  columnId,
  columns,
  members,
  role,
  dnd,
  onClose,
  onSaved,
  onDeleted,
}: CardDetailModalProps) {
  const api = useApi();
  const handleError = useErrorHandler();
  const { user } = useAuth();
  const roles = rolesFor(role);
  const canEdit = roles.canWrite;
  const canDelete = canEdit && (roles.canManage || (user !== null && card.created_by === user.id));

  const [formCardId, setFormCardId] = useState(card.id);
  const [title, setTitle] = useState(card.title);
  const [description, setDescription] = useState(card.description ?? "");
  // Empty string is the "no assignee" option.
  const [assignee, setAssignee] = useState(card.assignee_id ?? "");
  const [completed, setCompleted] = useState(card.completed_at !== null);
  const [errors, setErrors] = useState<Partial<Record<FormField_, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // The modal shows another card only when the parent passes a different card id. Edits to
  // the same card keep the entered values, so this runs during render, not in an effect.
  if (formCardId !== card.id) {
    setFormCardId(card.id);
    setTitle(card.title);
    setDescription(card.description ?? "");
    setAssignee(card.assignee_id ?? "");
    setCompleted(card.completed_at !== null);
    setErrors({});
    setFormError(null);
  }

  const values: CardFieldValues = {
    title: title.trim(),
    description,
    assignee_id: assignee === "" ? null : assignee,
    completed,
  };
  const changed = changedCardFields(card, values);
  const sortedColumns = sortByOrder(columns);

  function handleColumnChange(event: ChangeEvent<HTMLSelectElement>) {
    const targetColumnId = event.target.value;
    if (targetColumnId === columnId) {
      return;
    }
    // Same request as drag and drop, so the update and any revert are shared (FE-DND-05).
    void dnd.moveCard(card.id, targetColumnId, "end");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || changed.length === 0) {
      return;
    }
    const titleError = validateRequiredText("Title", title, LIMITS.title);
    const descriptionError = validateOptionalText("Description", description, LIMITS.description);
    const nextErrors: Partial<Record<FormField_, string>> = {};
    if (titleError !== null) {
      nextErrors.title = titleError;
    }
    if (descriptionError !== null) {
      nextErrors.description = descriptionError;
    }
    setErrors(nextErrors);
    setFormError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }
    const body: Partial<Record<CardField, unknown>> = {};
    for (const field of changed) {
      body[field] = values[field];
    }
    setSaving(true);
    try {
      const updated = await api.patch<Card>(`/api/cards/${card.id}`, body);
      setSaving(false);
      showSuccessToast("Card saved.");
      onSaved(updated);
    } catch (caught) {
      // The modal stays open with the entered values, and submit is enabled again (FE-FRM-03).
      setSaving(false);
      if (caught instanceof ApiError && caught.statusCode === 422 && caught.details !== null) {
        const { mapped, unmatched } = mapFieldDetails(caught, ["title", "description"] as const);
        setErrors(mapped);
        if (unmatched.length > 0) {
          setFormError(unmatched.join(" "));
        }
        return;
      }
      handleError(caught);
    }
  }

  async function handleDelete() {
    if (deleting) {
      return;
    }
    setDeleting(true);
    try {
      await api.delete<void>(`/api/cards/${card.id}`);
      setDeleting(false);
      setConfirmOpen(false);
      onDeleted(card.id);
      onClose();
    } catch (caught) {
      // The confirmation stays open so the user can retry or cancel.
      setDeleting(false);
      handleError(caught);
    }
  }

  return (
    <>
      <BaseModal open title="Edit card" onClose={onClose} size="lg" dismissDisabled={saving || deleting}>
        <div className="flex flex-col gap-4">
          {canEdit ? (
            <FormField label="Column">
              {(control) => (
                <select
                  {...control}
                  name="column"
                  value={columnId}
                  onChange={handleColumnChange}
                  className={INPUT_CLASSES}
                >
                  {sortedColumns.map((column) => (
                    <option key={column.id} value={column.id}>
                      {column.name}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
          ) : (
            <ReadOnlyNotice role={role} />
          )}

          {canEdit ? (
            <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
              <FormAlert message={formError} />
              <FormField label="Title" error={errors.title}>
                {(control) => (
                  <input
                    {...control}
                    type="text"
                    name="title"
                    autoComplete="off"
                    value={title}
                    onChange={(event) => {
                      setTitle(event.target.value);
                      setErrors((current) => ({ ...current, title: undefined }));
                    }}
                    className={INPUT_CLASSES}
                  />
                )}
              </FormField>
              <FormField label="Description" error={errors.description}>
                {(control) => (
                  <textarea
                    {...control}
                    name="description"
                    rows={4}
                    value={description}
                    onChange={(event) => {
                      setDescription(event.target.value);
                      setErrors((current) => ({ ...current, description: undefined }));
                    }}
                    className={INPUT_CLASSES}
                  />
                )}
              </FormField>
              <FormField label="Assignee">
                {(control) => (
                  <select
                    {...control}
                    name="assignee"
                    value={assignee}
                    onChange={(event) => setAssignee(event.target.value)}
                    className={INPUT_CLASSES}
                  >
                    <option value="">Unassigned</option>
                    {members.map((member) => (
                      <option key={member.user_id} value={member.user_id}>
                        {member.name}
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
              <FormField label="Completed">
                {(control) => (
                  <input
                    {...control}
                    type="checkbox"
                    name="completed"
                    checked={completed}
                    onChange={(event) => setCompleted(event.target.checked)}
                    className="h-4 w-4"
                  />
                )}
              </FormField>
              <div className="flex justify-end">
                <BaseButton type="submit" loading={saving} disabled={changed.length === 0}>
                  Save changes
                </BaseButton>
              </div>
            </form>
          ) : (
            <div className="flex flex-col gap-2">
              <h3 className="text-lg font-semibold text-gray-900">{card.title}</h3>
              {card.description !== null && card.description !== "" ? (
                <p className="whitespace-pre-wrap break-words text-base text-gray-800">
                  {card.description}
                </p>
              ) : null}
            </div>
          )}

          {canDelete ? (
            <div className="flex justify-start">
              <BaseButton variant="destructive" onClick={() => setConfirmOpen(true)}>
                Delete card
              </BaseButton>
            </div>
          ) : null}

          <CommentList cardId={card.id} canWrite={canEdit} />
        </div>
      </BaseModal>
      <ConfirmModal
        open={confirmOpen}
        title="Delete card"
        message="Delete this card? This cannot be undone."
        confirmLabel="Delete"
        pending={deleting}
        onConfirm={() => void handleDelete()}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
