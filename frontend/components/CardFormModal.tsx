"use client";

import { useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { FormField } from "@/components/shared/FormField";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { success as showSuccessToast } from "@/lib/toast";
import type { Card, Member } from "@/lib/types";
import { validateOptionalText, validateRequiredText } from "@/lib/validation";

const CARD_TITLE_MAX = 255;
const CARD_DESCRIPTION_MAX = 10_000;

export interface CardFormModalProps {
  open: boolean;
  columnId: string;
  members: Member[];
  onClose: () => void;
  // Receives the card returned by the API (status 201) so the parent can append it.
  onCreated: (card: Card) => void;
}

// Creates a card in a column (Requirements 12.1 to 12.3, 12.8, 12.9).
export function CardFormModal({
  open,
  columnId,
  members,
  onClose,
  onCreated,
}: CardFormModalProps) {
  const api = useApi();
  const handleError = useErrorHandler();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  // Empty string is the "no assignee" option, which is selected by default.
  const [assignee, setAssignee] = useState("");
  const [titleError, setTitleError] = useState<string | null>(null);
  const [descriptionError, setDescriptionError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [wasOpen, setWasOpen] = useState(open);

  // The modal stays mounted between openings, so each opening starts from empty values.
  // This runs during render, not in an effect, to avoid a cascading render.
  if (wasOpen !== open) {
    setWasOpen(open);
    if (open) {
      setTitle("");
      setDescription("");
      setAssignee("");
      setTitleError(null);
      setDescriptionError(null);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
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

    setPending(true);
    try {
      const card = await api.post<Card>(`/api/columns/${columnId}/cards`, {
        title: title.trim(),
        description,
        assignee_id: assignee || null,
      });
      // The component stays mounted after the modal closes, so the pending flag is cleared
      // here as well. Otherwise a reopened modal would start with a disabled submit.
      setPending(false);
      onCreated(card);
      onClose();
      showSuccessToast("Card created.");
    } catch (caught) {
      // The modal stays open with the entered values, and submit is enabled again.
      setPending(false);
      handleError(caught);
    }
  }

  return (
    <BaseModal open={open} title="Add card" onClose={onClose} size="lg">
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

        <FormField label="Description" error={descriptionError}>
          {(control) => (
            <textarea
              {...control}
              name="description"
              rows={4}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 aria-[invalid=true]:border-red-600"
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
              className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900"
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

        <div className="flex justify-end gap-2">
          <BaseButton variant="secondary" onClick={onClose}>
            Cancel
          </BaseButton>
          <BaseButton type="submit" loading={pending}>
            Create
          </BaseButton>
        </div>
      </form>
    </BaseModal>
  );
}
