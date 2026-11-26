import { act, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProfileForm } from "@/components/ProfileForm";
import { AuthContext, type AuthContextValue } from "@/context/AuthContext";
import { ApiError } from "@/lib/errors";
import type { User } from "@/types/api";

const api = vi.hoisted(() => ({ patch: vi.fn() }));

vi.mock("@/hooks/useApi", () => ({
  useApi: () => api,
}));

vi.mock("@/lib/toast", () => ({
  error: vi.fn(),
  success: vi.fn(),
  loading: vi.fn(),
  dismiss: vi.fn(),
  showSessionExpiredToast: vi.fn(),
}));

const user = {
  id: "user-1",
  name: "Ana",
  email: "ana@example.com",
  created_at: "2026-01-01T00:00:00Z",
} as User;

let auth: AuthContextValue;

function renderForm() {
  function wrapper({ children }: { children: ReactNode }) {
    return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
  }
  return render(<ProfileForm />, { wrapper });
}

describe("ProfileForm (FE-PAGE-06, FE-FRM-02, FE-FRM-03)", () => {
  beforeEach(() => {
    api.patch.mockReset();
    auth = {
      token: "t",
      user,
      updateUser: vi.fn(),
      clearSession: vi.fn(),
      logout: vi.fn(async () => undefined),
      expireSession: vi.fn(async () => undefined),
    };
  });

  it("keeps Save disabled until a field changes", () => {
    renderForm();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ana K." } });
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled();
  });

  it("shows an invalid email inline and sends no request", () => {
    renderForm();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "not-an-email" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Enter a valid email address.")).toBeInTheDocument();
    expect(api.patch).not.toHaveBeenCalled();
  });

  it("maps 422 details onto the matching field and sends only the changed field", async () => {
    api.patch.mockRejectedValueOnce(
      new ApiError(422, "Invalid request data.", "VALIDATION_ERROR", {
        name: ["Name has invalid characters."],
      }),
    );
    renderForm();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ana K." } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Name has invalid characters.")).toBeInTheDocument();
    expect(api.patch).toHaveBeenCalledWith("/api/users/me", { name: "Ana K." });
    expect(screen.getByLabelText("Name")).toHaveValue("Ana K.");
  });

  it("shows a 409 email conflict on the email field", async () => {
    api.patch.mockRejectedValueOnce(new ApiError(409, "Email taken.", "EMAIL_TAKEN"));
    renderForm();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "taken@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Email already in use.")).toBeInTheDocument();
  });

  it("blocks a second submit while the first request is pending", async () => {
    let finish: () => void = () => undefined;
    api.patch.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          finish = () => resolve({ ...user, name: "Ana K." });
        }),
    );
    renderForm();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Ana K." } });
    const form = screen.getByRole("button", { name: "Save" }).closest("form") as HTMLFormElement;
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(api.patch).toHaveBeenCalledTimes(1);
    await act(async () => {
      finish();
    });
  });
});
