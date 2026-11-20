"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import { success as showSuccessToast } from "@/lib/toast";
import type { LoginResponse, RegisteredUser } from "@/lib/types";
import { validateRegister, type FieldErrors } from "@/lib/validation";
import { BaseButton } from "@/components/shared/BaseButton";
import { FormAlert } from "@/components/shared/FormAlert";
import { FormField } from "@/components/shared/FormField";

type RegisterField = "name" | "email" | "password";

interface RegisterValues {
  name: string;
  email: string;
  password: string;
}

const EMPTY_VALUES: RegisterValues = { name: "", email: "", password: "" };

const INPUT_CLASSES =
  "rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus-visible:outline-2 focus-visible:outline-blue-600 aria-[invalid=true]:border-red-600";

export function RegisterForm() {
  const router = useRouter();
  const { token, login } = useAuth();
  const api = useApi();
  const handleError = useErrorHandler();

  const [values, setValues] = useState<RegisterValues>(EMPTY_VALUES);
  const [errors, setErrors] = useState<FieldErrors<RegisterField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  // Signed-in visitors are sent to the dashboard instead of the form.
  useEffect(() => {
    if (token) {
      router.replace("/");
    }
  }, [token, router]);

  if (token) {
    return null;
  }

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
    if (Object.keys(validation).length > 0) {
      return;
    }

    setFormError(null);
    setPending(true);
    const email = values.email.trim();

    try {
      await api.post<RegisteredUser>("/api/auth/register", {
        name: values.name,
        email,
        password: values.password,
      });
    } catch (error) {
      setPending(false);
      if (error instanceof ApiError && (error.statusCode === 409 || error.statusCode === 400)) {
        setFormError(error.message);
      } else {
        handleError(error);
      }
      return;
    }

    // The register response carries no token, so sign in with the same credentials.
    let session: LoginResponse;
    try {
      session = await api.post<LoginResponse>("/api/auth/login", {
        email,
        password: values.password,
      });
    } catch {
      setValues(EMPTY_VALUES);
      setPending(false);
      showSuccessToast("Account created. Please log in.");
      router.replace("/login");
      return;
    }

    login(session.access_token, session.expires_in, session.user);
    showSuccessToast("Welcome to RevoTask!");
    router.replace("/");
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
