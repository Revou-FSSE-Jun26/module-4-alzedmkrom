"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseModal } from "@/components/shared/BaseModal";
import { FormField } from "@/components/shared/FormField";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { success as showSuccessToast } from "@/lib/toast";
import type { Board } from "@/types/api";
import { LIMITS, validateRequiredText } from "@/lib/validation";



// Dashboard trigger and dialog for creating a board (Requirement 9.3 to 9.6).
export function CreateBoardModal() {
  const router = useRouter();
  const api = useApi();
  const handleError = useErrorHandler();

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function openModal() {
    setName("");
    setNameError(null);
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

    const validationError = validateRequiredText("Name", name, LIMITS.boardName);
    setNameError(validationError);
    if (validationError !== null) {
      return;
    }

    setPending(true);
    try {
      const board = await api.post<Board>("/api/boards", { name: name.trim() });
      // The component stays mounted after the modal closes, so the pending flag is cleared
      // here as well. Otherwise a reopened modal would start with a disabled submit.
      setPending(false);
      setOpen(false);
      showSuccessToast("Board created.");
      router.push("/boards/" + board.id);
    } catch (caught) {
      setPending(false);
      handleError(caught);
    }
  }

  return (
    <>
      <BaseButton onClick={openModal}>Create board</BaseButton>

      <BaseModal open={open} title="Create board" onClose={closeModal} dismissDisabled={pending}>
        <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
          <FormField label="Name" error={nameError}>
            {(control) => (
              <input
                {...control}
                type="text"
                name="name"
                autoComplete="off"
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900 aria-[invalid=true]:border-red-600"
              />
            )}
          </FormField>

          <div className="flex justify-end gap-2">
            <BaseButton variant="secondary" onClick={closeModal}>
              Cancel
            </BaseButton>
            <BaseButton type="submit" loading={pending}>
              Create
            </BaseButton>
          </div>
        </form>
      </BaseModal>
    </>
  );
}
