import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useRouter } from "next/navigation";
import type { Mock } from "vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { loginAction } from "@/app/actions/session";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { AuthContext, type AuthContextValue } from "@/context/AuthContext";
import { ApiError } from "@/lib/errors";

// The form uses useErrorHandler, which reads AuthContext. Signed out, so no user and no token.
const signedOut: AuthContextValue = {
  token: null,
  user: null,
  updateUser: vi.fn(),
  clearSession: vi.fn(),
  logout: vi.fn(async () => undefined),
  expireSession: vi.fn(async () => undefined),
};

function renderRegister() {
  function wrapper({ children }: { children: ReactNode }) {
    return <AuthContext.Provider value={signedOut}>{children}</AuthContext.Provider>;
  }
  return render(<RegisterForm />, { wrapper });
}

const api = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock("@/hooks/useApi", () => ({
  useApi: () => api,
}));

vi.mock("@/app/actions/session", () => ({
  loginAction: vi.fn(),
}));

vi.mock("@/lib/toast", () => ({
  error: vi.fn(),
  success: vi.fn(),
  loading: vi.fn(),
  dismiss: vi.fn(),
  showSessionExpiredToast: vi.fn(),
}));

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText("Name", { exact: true }), { target: { value: "Ana" } });
  fireEvent.change(screen.getByLabelText("Email", { exact: true }), {
    target: { value: " Ana@Example.com " },
  });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), {
    target: { value: "longenough1" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
}

describe("RegisterForm auto-login (FE-PAGE-01)", () => {
  let router: { replace: Mock; refresh: Mock };

  beforeEach(() => {
    api.post.mockReset();
    vi.mocked(loginAction).mockReset();
    router = vi.mocked(useRouter)() as unknown as { replace: Mock; refresh: Mock };
    router.replace.mockClear();
    router.refresh.mockClear();
  });

  it("signs the new user in with the same credentials and opens the dashboard", async () => {
    api.post.mockResolvedValueOnce({ id: "u1", name: "Ana", email: "ana@example.com" });
    vi.mocked(loginAction).mockResolvedValueOnce({ ok: true });
    renderRegister();
    fillAndSubmit();
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/"));
    // The form trims the email but does not lowercase it. The API lowercases it (BE-VAL-03).
    expect(api.post).toHaveBeenCalledWith("/api/auth/register", {
      name: "Ana",
      email: "Ana@Example.com",
      password: "longenough1",
    });
    expect(loginAction).toHaveBeenCalledWith("Ana@Example.com", "longenough1");
    expect(router.refresh).toHaveBeenCalled();
    expect(router.replace).not.toHaveBeenCalledWith("/login");
  });

  it("falls back to the login page when auto-login fails", async () => {
    api.post.mockResolvedValueOnce({ id: "u1", name: "Ana", email: "ana@example.com" });
    vi.mocked(loginAction).mockResolvedValueOnce({
      ok: false,
      statusCode: 401,
      message: "Invalid email or password",
    });
    renderRegister();
    fillAndSubmit();
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/login"));
  });

  it("shows a duplicate email on the field and does not try to log in", async () => {
    api.post.mockRejectedValueOnce(new ApiError(409, "Email taken.", "EMAIL_TAKEN"));
    renderRegister();
    fillAndSubmit();
    expect(await screen.findByText("Email already in use.")).toBeInTheDocument();
    expect(loginAction).not.toHaveBeenCalled();
  });
});
