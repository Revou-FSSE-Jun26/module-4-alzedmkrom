"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { loginAction } from "@/app/actions/session";
import { BaseButton } from "@/components/shared/BaseButton";
import { FormAlert } from "@/components/shared/FormAlert";
import { FormField } from "@/components/shared/FormField";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import { success as showSuccessToast } from "@/lib/toast";
import { validateRegister, type FieldErrors } from "@/lib/validation";
import type { PublicUser } from "@/types/api";

type RegisterField = "name" | "email" | "password";

interface RegisterValues {
  name: string;
  email: string;
  password: string;
}

const EMPTY_VALUES: RegisterValues = { name: "", email: "", password: "" };

const INPUT_CLASSES =
  "rounded-md border border-gray-300 bg-white px-3 py-2 text-base text-gray-900 focus-visible:outline-2 focus-visible:outline-blue-600 aria-[invalid=true]:border-red-600";

// Registration creates an account, then signs the user in with the same credentials (FE-PAGE-01).
// The API returns no token on register.
export function RegisterForm() {
  const router = useRouter();
  const api = useApi();
  const handleError = useErrorHandler();
  const [values, setValues] = useState<RegisterValues>(EMPTY_VALUES);
  const [errors, setErrors] = useState<FieldErrors<RegisterField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function updateField(field: RegisterField, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }
    const validation = validateRegister(values);
    setErrors(validation);
    setFormError(null);
    if (Object.keys(validation).length > 0) {
      return;
    }
    setPending(true);
    try {
      await api.post<PublicUser>("/api/auth/register", {
        name: values.name.trim(),
        email: values.email.trim(),
        password: values.password,
      });
    } catch (error) {
      setPending(false);
      if (error instanceof ApiError && error.statusCode === 409 && error.code === "EMAIL_TAKEN") {
        setErrors({ email: "Email already in use." });
        return;
      }
      if (error instanceof ApiError && error.statusCode === 422 && error.details !== null) {
        const mapped: FieldErrors<RegisterField> = {};
        for (const field of ["name", "email", "password"] as const) {
          const messages = error.details[field];
          if (messages !== undefined && messages.length > 0) {
            mapped[field] = messages[0];
          }
        }
        setErrors(mapped);
        if (Object.keys(mapped).length === 0) {
          handleError(error);
        }
        return;
      }
      // Input stays in the form on every other error (FE-FRM-03).
      handleError(error);
      return;
    }
    // The register response has no token, so sign in with the same credentials (FE-PAGE-01).
    const login = await loginAction(values.email.trim(), values.password);
    if (login.ok) {
      showSuccessToast("Account created.");
      router.replace("/");
      router.refresh();
      return;
    }
    showSuccessToast("Account created. Please log in.");
    router.replace("/login");
  }

  return (
    <form
      noValidate
      onSubmit={handleSubmit}
      className="mx-auto flex w-full max-w-sm flex-col gap-4"
    >
      <h1 className="text-2xl font-semibold text-gray-900">Create account</h1>
      <FormAlert message={formError} />
      <FormField label="Name" error={errors.name}>
        {(control) => (
          <input
            {...control}
            name="name"
            type="text"
            autoComplete="name"
            value={values.name}
            onChange={(event) => updateField("name", event.target.value)}
            className={INPUT_CLASSES}
          />
        )}
      </FormField>
      <FormField label="Email" error={errors.email}>
        {(control) => (
          <input
            {...control}
            name="email"
            type="email"
            autoComplete="email"
            value={values.email}
            onChange={(event) => updateField("email", event.target.value)}
            className={INPUT_CLASSES}
          />
        )}
      </FormField>
      <FormField label="Password" error={errors.password} hint="8 to 128 characters">
        {(control) => (
          <input
            {...control}
            name="password"
            type="password"
            autoComplete="new-password"
            value={values.password}
            onChange={(event) => updateField("password", event.target.value)}
            className={INPUT_CLASSES}
          />
        )}
      </FormField>
      <BaseButton type="submit" loading={pending} className="w-full">
        Create account
      </BaseButton>
    </form>
  );
}
