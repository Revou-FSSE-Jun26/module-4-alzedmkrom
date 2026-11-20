"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { FormAlert } from "@/components/shared/FormAlert";
import { FormField } from "@/components/shared/FormField";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import type { LoginResponse } from "@/lib/types";
import { validateLogin, type FieldErrors } from "@/lib/validation";

const SESSION_EXPIRED_MESSAGE = "Your session has expired. Please log in again.";

type LoginField = "email" | "password";

export interface LoginFormProps {
  sessionExpired: boolean;
}

export function LoginForm({ sessionExpired }: LoginFormProps) {
  const router = useRouter();
  const { token, login, clearSession } = useAuth();
  const api = useApi();
  const handleError = useErrorHandler();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<LoginField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const alreadySignedIn = token !== null && !sessionExpired;

  // A held token means the user is already signed in (4.7). The effect only
  // runs after render, so the form is not shown on the first client pass.
  useEffect(() => {
    if (alreadySignedIn) {
      router.replace("/");
    }
  }, [alreadySignedIn, router]);

  // The session-expired redirect ends the session in state and in the cookie (2.4, F4).
  useEffect(() => {
    if (sessionExpired) {
      clearSession();
    }
  }, [sessionExpired, clearSession]);

  if (alreadySignedIn) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) {
      return;
    }

    const errors = validateLogin({ email, password });
    setFieldErrors(errors);
    setFormError(null);
    if (errors.email !== undefined || errors.password !== undefined) {
      return;
    }

    setPending(true);
    try {
      const response = await api.post<LoginResponse>("/api/auth/login", { email, password });
      login(response.access_token, response.expires_in, response.user);
      // The button stays disabled until the navigation replaces this page.
      router.replace("/");
    } catch (error) {
      if (error instanceof ApiError && error.statusCode === 401) {
        setFormError(error.message);
      } else {
        handleError(error);
      }
      setPending(false);
    }
  }

  const alertMessage = formError ?? (sessionExpired ? SESSION_EXPIRED_MESSAGE : null);

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-6 px-4 py-12">
      <h1 className="text-2xl font-semibold text-gray-900">Log in</h1>

      <FormAlert message={alertMessage} />

      <form className="flex flex-col gap-4" noValidate onSubmit={handleSubmit}>
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

        <FormField label="Password" error={fieldErrors.password}>
          {(control) => (
            <input
              {...control}
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 aria-[invalid=true]:border-red-600"
            />
          )}
        </FormField>

        <BaseButton type="submit" loading={pending} className="min-h-10 w-full">
          Log in
        </BaseButton>
      </form>

      <p className="text-sm text-gray-700">
        No account yet?{" "}
        <Link href="/register" className="font-medium text-blue-700 underline">
          Create one
        </Link>
      </p>
    </main>
  );
}
