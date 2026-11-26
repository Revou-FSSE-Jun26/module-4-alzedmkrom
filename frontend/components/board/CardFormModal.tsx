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
import { success as showSuccessToast } from "@/lib/toast";
import { LIMITS, validateOptionalText, validateRequiredText } from "@/lib/validation";
import type { Card, Member } from "@/types/api";

type CardFormField = "title" | "description";

export interface CardFormModalProps {
  open: boolean;
  columnId: string;
  members: Member[];
  onClose: () => void;
  /** Receives the card returned by the API (status 201) so the parent can append it. */
  onCreated: (card: Card) => void;
}

// Creates a card in a column (FE-PAGE-07).
export function CardFormModal({ open, columnId, members, onClose, onCreated }: CardFormModalProps) {
  const api = useApi();
  const handleError = useErrorHandler();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  // Empty string is the "no assignee" option, which is selected by default.
  const [assignee, setAssignee] = useState("");
  const [errors, setErrors] = useState<Partial<Record<CardFormField, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
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
      setErrors({});
      setFormError(null);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }
    const titleError = validateRequiredText("Title", title, LIMITS.title);
    const descriptionError = validateOptionalText("Description", description, LIMITS.description);
    const nextErrors: Partial<Record<CardFormField, string>> = {};
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
    setPending(true);
    try {
      const card = await api.post<Card>(`/api/columns/${columnId}/cards`, {
        title: title.trim(),
        description,
        assignee_id: assignee || null,
      });
      setPending(false);
      onCreated(card);
      onClose();
      showSuccessToast("Card created.");
    } catch (caught) {
      // The modal stays open with the entered values, and submit is enabled again (FE-FRM-03).
      setPending(false);
      if (caught instanceof ApiError && caught.statusCode === 422 && caught.details !== null) {
        const { mapped, unmatched } = mapFieldDetails(caught, ["title", "description"] as const);
        setErrors(mapped);
        setFormError(unmatched.length > 0 ? unmatched.join(" ") : null);
        return;
      }
      handleError(caught);
    }
  }

  return (
    <BaseModal open={open} title="Add card" onClose={onClose} size="lg" dismissDisabled={pending}>
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
              className="rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900 aria-[invalid=true]:border-red-600"
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
              className="rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900 aria-[invalid=true]:border-red-600"
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
              className="rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900"
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
