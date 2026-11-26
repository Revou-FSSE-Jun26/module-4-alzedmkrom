"use client";

import { useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { FormAlert } from "@/components/shared/FormAlert";
import { FormField } from "@/components/shared/FormField";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import { mapFieldDetails } from "@/lib/formErrors";
import { success as showSuccessToast } from "@/lib/toast";
import {
  changedProfileFields,
  validateProfile,
  type FieldErrors,
  type ProfileField,
} from "@/lib/validation";
import type { User } from "@/types/api";

const INPUT_CLASSES =
  "rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900 aria-[invalid=true]:border-red-600";

interface ProfileBody {
  name?: string;
  email?: string;
}

// Profile form (FE-PAGE-06). Sends only the fields that changed. There is no password or role field.
export function ProfileForm() {
  const { user, updateUser } = useAuth();
  const api = useApi();
  const handleError = useErrorHandler();
  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<ProfileField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  // The profile page is protected, so a null user only happens during sign-out. Nothing is shown then.
  if (user === null) {
    return null;
  }

  const changed = changedProfileFields(user, { name, email });
  const submitDisabled = changed.length === 0 || pending;

  function cancel() {
    setName(user?.name ?? "");
    setEmail(user?.email ?? "");
    setFieldErrors({});
    setFormError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitDisabled) {
      return;
    }
    const errors = validateProfile({ name, email });
    setFieldErrors(errors);
    setFormError(null);
    if (errors.name !== undefined || errors.email !== undefined) {
      return;
    }
    // Only the changed fields go to the API. The email is sent trimmed.
    const body: ProfileBody = {};
    if (changed.includes("name")) {
      body.name = name.trim();
    }
    if (changed.includes("email")) {
      body.email = email.trim();
    }
    setPending(true);
    try {
      const updated = await api.patch<User>("/api/users/me", body);
      updateUser(updated);
      setName(updated.name);
      setEmail(updated.email);
      setPending(false);
      showSuccessToast("Profile updated.");
    } catch (error) {
      setPending(false);
      if (error instanceof ApiError && error.statusCode === 409) {
        setFieldErrors({ email: "Email already in use." });
        return;
      }
      if (error instanceof ApiError && error.statusCode === 422 && error.details !== null) {
        const { mapped, unmatched } = mapFieldDetails(error, ["name", "email"] as const);
        setFieldErrors(mapped);
        setFormError(unmatched.length > 0 ? unmatched.join(" ") : null);
        return;
      }
      // Input stays in the form on every other error (FE-FRM-03).
      handleError(error);
    }
  }

  return (
    <section className="flex w-full max-w-md flex-col gap-6">
      <h1 className="text-2xl font-semibold text-gray-900">Profile</h1>
      <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
        <FormAlert message={formError} />
        <FormField label="Name" error={fieldErrors.name}>
          {(control) => (
            <input
              {...control}
              type="text"
              name="name"
              autoComplete="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={INPUT_CLASSES}
            />
          )}
        </FormField>
        <FormField label="Email" error={fieldErrors.email}>
          {(control) => (
            <input
              {...control}
              type="email"
              name="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={INPUT_CLASSES}
            />
          )}
        </FormField>
        <div className="flex justify-end gap-2">
          <BaseButton variant="secondary" onClick={cancel} disabled={pending || changed.length === 0}>
            Cancel
          </BaseButton>
          <BaseButton type="submit" disabled={submitDisabled} loading={pending}>
            Save
          </BaseButton>
        </div>
      </form>
    </section>
  );
}
