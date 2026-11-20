"use client";

import { useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { FormField } from "@/components/shared/FormField";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import { success as showSuccessToast } from "@/lib/toast";
import type { User } from "@/lib/types";
import {
  changedProfileFields,
  validateProfile,
  type FieldErrors,
  type ProfileField,
} from "@/lib/validation";

const PROFILE_UPDATED_MESSAGE = "Profile updated.";

interface ProfileBody {
  name?: string;
  email?: string;
}

export function ProfileForm() {
  const { user, updateUser } = useAuth();
  const api = useApi();
  const handleError = useErrorHandler();

  const [name, setName] = useState(user?.name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<ProfileField>>({});
  const [pending, setPending] = useState(false);

  // The profile page sits behind the Route_Guard, so a null user only occurs
  // during a sign-out. Nothing is shown then.
  if (user === null) {
    return null;
  }

  const changed = changedProfileFields(user, { name, email });
  const submitDisabled = changed.length === 0 || pending;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitDisabled) {
      return;
    }

    const errors = validateProfile({ name, email });
    setFieldErrors(errors);
    if (errors.name !== undefined || errors.email !== undefined) {
      return;
    }

    // Only the changed fields go to the API, and the email is sent trimmed (17.4).
    const body: ProfileBody = {};
    if (changed.includes("name")) {
      body.name = name;
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
      showSuccessToast(PROFILE_UPDATED_MESSAGE);
    } catch (error) {
      if (error instanceof ApiError && error.statusCode === 409) {
        setFieldErrors({ email: error.message });
      } else {
        handleError(error);
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="flex w-full max-w-md flex-col gap-6">
      <h1 className="text-2xl font-semibold text-gray-900">Profile</h1>

      <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
        <FormField label="Name" error={fieldErrors.name}>
          {(control) => (
            <input
              {...control}
              type="text"
              name="name"
              autoComplete="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 aria-[invalid=true]:border-red-600"
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
              className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 aria-[invalid=true]:border-red-600"
            />
          )}
        </FormField>

        <BaseButton
          type="submit"
          variant="primary"
          disabled={submitDisabled}
          loading={pending}
          className="min-h-10 w-full"
        >
          Save changes
        </BaseButton>
      </form>
    </section>
  );
}
