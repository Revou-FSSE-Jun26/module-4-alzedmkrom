"use client";

import { useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { FormField } from "@/components/shared/FormField";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { success as showSuccessToast } from "@/lib/toast";
import type { Member, MemberRole } from "@/types/api";
import { LIMITS, validateEmail } from "@/lib/validation";

const INPUT_CLASSES =
  "rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900 aria-[invalid=true]:border-red-600";

export interface AddMemberModalProps {
  boardId: string;
  onAdded: (member: Member) => void;
}

// Members-page trigger and dialog for adding a member (Requirements 19.2 to 19.4, 19.8).
export function AddMemberModal({ boardId, onAdded }: AddMemberModalProps) {
  const api = useApi();
  const handleError = useErrorHandler();

  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<MemberRole>("member");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function openModal() {
    setEmail("");
    setRole("member");
    setEmailError(null);
    setOpen(true);
  }

  function closeModal() {
    setOpen(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }

    const validationError = validateEmail(email);
    setEmailError(validationError);
    if (validationError !== null) {
      return;
    }

    setPending(true);
    try {
      const member = await api.post<Member>(`/api/boards/${boardId}/members`, {
        email: email.trim(),
        role,
      });
      // The component stays mounted after the modal closes, so the pending flag is cleared
      // here as well. Otherwise a reopened modal would start with a disabled submit.
      setPending(false);
      onAdded(member);
      setOpen(false);
      showSuccessToast("Member added.");
    } catch (caught) {
      // The modal stays open with the entered values, and submit is enabled again.
      setPending(false);
      handleError(caught);
    }
  }

  return (
    <>
      <BaseButton onClick={openModal}>Add member</BaseButton>

      <BaseModal open={open} title="Add member" onClose={closeModal} dismissDisabled={pending}>
        <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
          <FormField label="Email" error={emailError}>
            {(control) => (
              <input
                {...control}
                type="email"
                name="email"
                autoComplete="off"
                maxLength={LIMITS.emailMax}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className={INPUT_CLASSES}
              />
            )}
          </FormField>

          <FormField label="Role">
            {(control) => (
              <select
                {...control}
                name="role"
                value={role}
                onChange={(event) => setRole(event.target.value as MemberRole)}
                className={INPUT_CLASSES}
              >
                <option value="member">member</option>
                <option value="admin">admin</option>
              </select>
            )}
          </FormField>

          <div className="flex justify-end gap-2">
            <BaseButton variant="secondary" onClick={closeModal}>
              Cancel
            </BaseButton>
            <BaseButton type="submit" loading={pending}>
              Add
            </BaseButton>
          </div>
        </form>
      </BaseModal>
    </>
  );
}
