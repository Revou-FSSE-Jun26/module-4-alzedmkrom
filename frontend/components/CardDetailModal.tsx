"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { ConfirmModal } from "@/components/shared/ConfirmModal";
import { FormField } from "@/components/shared/FormField";
import { CommentList } from "@/components/CommentList";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import type { DragAndDrop } from "@/hooks/useDragAndDrop";
import { sortByOrder } from "@/lib/collections";
import type { Card, Column, DeletedId, Member, Role } from "@/lib/types";
import {
  changedCardFields,
  validateOptionalText,
  validateRequiredText,
  type CardField,
  type CardFieldValues,
} from "@/lib/validation";

const CARD_TITLE_MAX = 255;
const CARD_DESCRIPTION_MAX = 10_000;

const INPUT_CLASSES =
  "rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 aria-[invalid=true]:border-red-600";

export interface CardDetailModalProps {
  card: Card;
  // The column that holds the card. The Column select shows this value.
  columnId: string;
  columns: readonly Column[];
  members: readonly Member[];
  boardRole: Role;
  dnd: DragAndDrop;
  onClose: () => void;
  // Receives the card returned by PATCH /api/cards/<id>.
  onSaved: (card: Card) => void;
  onDeleted: (cardId: string) => void;
}

// Edit form, column move, delete and comments for one card (Requirements 12.4
// to 12.8, 12.10, 12.11, 13.13, 14.1).
export function CardDetailModal({
  card,
  columnId,
  columns,
  members,
  boardRole,
  dnd,
  onClose,
  onSaved,
  onDeleted,
}: CardDetailModalProps) {
  const api = useApi();
  const handleError = useErrorHandler();
  const { user } = useAuth();

  const [formCardId, setFormCardId] = useState(card.id);
  const [title, setTitle] = useState(card.title);
  const [description, setDescription] = useState(card.description ?? "");
  // Empty string is the "no assignee" option.
  const [assignee, setAssignee] = useState(card.assignee_id ?? "");
  const [completed, setCompleted] = useState(card.completed_at !== null);
  const [titleError, setTitleError] = useState<string | null>(null);
  const [descriptionError, setDescriptionError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // The modal shows another card only when the parent passes a different card id.
  // Edits to the same card keep the entered values, so this runs during render, not in an effect.
  if (formCardId !== card.id) {
    setFormCardId(card.id);
    setTitle(card.title);
    setDescription(card.description ?? "");
    setAssignee(card.assignee_id ?? "");
    setCompleted(card.completed_at !== null);
    setTitleError(null);
    setDescriptionError(null);
  }

  const values: CardFieldValues = {
    title: title.trim(),
    description,
    assignee_id: assignee === "" ? null : assignee,
    completed,
  };
  const changed = changedCardFields(card, values);
  const canDelete = user !== null && (card.created_by === user.id || boardRole === "admin");
  const sortedColumns = sortByOrder(columns);

  function handleColumnChange(event: ChangeEvent<HTMLSelectElement>) {
    const targetColumnId = event.target.value;
    if (targetColumnId === columnId) {
      return;
    }
    // The select stays on columnId until the parent receives the moved card, so a failed move reverts it.
    void dnd.moveCard(card.id, targetColumnId, "end");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving || changed.length === 0) {
      return;
    }

    const nextTitleError = validateRequiredText("Title", title, CARD_TITLE_MAX);
    const nextDescriptionError = validateOptionalText(
      "Description",
      description,
      CARD_DESCRIPTION_MAX,
    );
    setTitleError(nextTitleError);
    setDescriptionError(nextDescriptionError);
    if (nextTitleError !== null || nextDescriptionError !== null) {
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
      onSaved(updated);
    } catch (caught) {
      // The modal stays open with the entered values, and submit is enabled again.
      setSaving(false);
      handleError(caught);
    }
  }

  async function handleDelete() {
    if (deleting) {
      return;
    }
    setDeleting(true);
    try {
      const result = await api.delete<DeletedId>(`/api/cards/${card.id}`);
      setDeleting(false);
      setConfirmOpen(false);
      onDeleted(result.id);
      onClose();
    } catch (caught) {
      // The confirmation stays open so the user can retry or cancel.
      setDeleting(false);
      handleError(caught);
    }
  }

  return (
    <>
      <BaseModal open title="Edit card" onClose={onClose} size="lg">
        <div className="flex flex-col gap-4">
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
                    {column.title}
                  </option>
                ))}
              </select>
            )}
          </FormField>

          <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
            <FormField label="Title" error={titleError}>
              {(control) => (
                <input
                  {...control}
                  type="text"
                  name="title"
                  autoComplete="off"
                  value={title}
                  onChange={(event) => {
                    setTitle(event.target.value);
                    setTitleError(null);
                  }}
                  className={INPUT_CLASSES}
                />
              )}
            </FormField>

            <FormField label="Description" error={descriptionError}>
              {(control) => (
                <textarea
                  {...control}
                  name="description"
                  rows={4}
                  value={description}
                  onChange={(event) => {
                    setDescription(event.target.value);
                    setDescriptionError(null);
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
              <BaseButton
                type="submit"
                loading={saving}
                disabled={changed.length === 0 || saving}
              >
                Save changes
              </BaseButton>
            </div>
          </form>

          {canDelete ? (
            <div className="flex justify-start">
              <BaseButton variant="destructive" onClick={() => setConfirmOpen(true)}>
                Delete card
              </BaseButton>
            </div>
          ) : null}

          <CommentList cardId={card.id} />
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
