"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { loginAction } from "@/app/actions/session";
import { BaseButton } from "@/components/shared/BaseButton";
import { FormAlert } from "@/components/shared/FormAlert";
import { FormField } from "@/components/shared/FormField";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import { safeNextPath } from "@/lib/session";
import { validateLogin, type FieldErrors } from "@/lib/validation";

type LoginField = "email" | "password";

export interface LoginFormProps {
  /** Same-origin path to open after login. Already checked by the page (FE-SEC-03). */
  next: string;
}

// Controlled login form (FE-PAGE-01, FE-FRM-01). The password goes to a Server Action,
// which stores the JWT in an httpOnly cookie (FE-AUTH-01).
export function LoginForm({ next }: LoginFormProps) {
  const router = useRouter();
  const handleError = useErrorHandler();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors<LoginField>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

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
    const result = await loginAction(email.trim(), password);
    if (result.ok) {
      router.replace(safeNextPath(next));
      router.refresh();
      return;
    }
    setPending(false);
    if (result.statusCode === 401) {
      setFormError(result.message);
      return;
    }
    handleError(new ApiError(result.statusCode, result.message));
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-6 px-4 py-12">
      <h1 className="text-2xl font-semibold text-gray-900">Log in</h1>
      <FormAlert message={formError} />
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
              className="rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900 aria-[invalid=true]:border-red-600"
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
              className="rounded-md border border-gray-300 px-3 py-2 text-base text-gray-900 aria-[invalid=true]:border-red-600"
            />
          )}
        </FormField>
        <BaseButton type="submit" loading={pending} className="min-h-10 w-full">
          Log in
        </BaseButton>
      </form>
      <p className="text-base text-gray-700">
        No account yet?{" "}
        <Link href="/register" className="font-medium text-blue-700 underline">
          Create one
        </Link>
      </p>
    </main>
  );
}
