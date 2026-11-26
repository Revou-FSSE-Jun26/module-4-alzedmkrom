import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "@/context/AuthContext";
import { describeError, useErrorHandler } from "@/hooks/useErrorHandler";
import { ApiError } from "@/lib/errors";
import { error as showErrorToast } from "@/lib/toast";

vi.mock("@/lib/toast", () => ({
  error: vi.fn(),
  success: vi.fn(),
  loading: vi.fn(),
  dismiss: vi.fn(),
  showSessionExpiredToast: vi.fn(),
}));

// One test per row of the FE-API-05 table.
describe("describeError (FE-API-05)", () => {
  it("401 ends the session and shows no extra toast", () => {
    expect(describeError(new ApiError(401, "x", "UNAUTHENTICATED"))).toEqual({
      message: null,
      endsSession: true,
      hasFieldDetails: false,
    });
  });

  it("403 shows the permission message", () => {
    expect(describeError(new ApiError(403, "x", "FORBIDDEN")).message).toBe(
      "You don't have permission to do that.",
    );
  });

  it("404 shows the missing-item message", () => {
    expect(describeError(new ApiError(404, "x", "NOT_FOUND")).message).toBe(
      "That item no longer exists.",
    );
  });

  it("409 shows the server message", () => {
    expect(describeError(new ApiError(409, "Column still has other cards.", "COLUMN_HAS_FOREIGN_WORK")).message).toBe(
      "Column still has other cards.",
    );
  });

  it("422 shows no toast when field details exist, and the generic check message otherwise", () => {
    const withDetails = describeError(
      new ApiError(422, "x", "VALIDATION_ERROR", { title: ["Too long."] }),
    );
    expect(withDetails).toEqual({ message: null, endsSession: false, hasFieldDetails: true });
    expect(describeError(new ApiError(422, "x", "VALIDATION_ERROR", null)).message).toBe(
      "Please check the highlighted fields.",
    );
  });

  it("network failure (0) shows the connection message", () => {
    expect(describeError(new ApiError(0, "x", "NETWORK_ERROR")).message).toBe(
      "Can't reach the server. Check your connection.",
    );
  });

  it("5xx and unknown errors show the generic message and never raw details", () => {
    expect(describeError(new ApiError(500, "stack trace", "INTERNAL_ERROR")).message).toBe(
      "Something went wrong. Please try again.",
    );
    expect(describeError(new Error("boom")).message).toBe("Something went wrong. Please try again.");
  });
});

describe("useErrorHandler", () => {
  let auth: AuthContextValue;

  function wrapper({ children }: { children: ReactNode }) {
    return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
  }

  beforeEach(() => {
    vi.mocked(showErrorToast).mockClear();
    auth = {
      token: "t",
      user: null,
      updateUser: vi.fn(),
      clearSession: vi.fn(),
      logout: vi.fn(async () => undefined),
      expireSession: vi.fn(async () => undefined),
    };
  });

  it("shows one toast for a 403", () => {
    const { result } = renderHook(() => useErrorHandler(), { wrapper });
    result.current(new ApiError(403, "x", "FORBIDDEN"));
    expect(showErrorToast).toHaveBeenCalledTimes(1);
    expect(showErrorToast).toHaveBeenCalledWith("You don't have permission to do that.");
  });

  it("runs the expiry flow for a 401 without a toast", () => {
    const { result } = renderHook(() => useErrorHandler(), { wrapper });
    result.current(new ApiError(401, "x", "UNAUTHENTICATED"));
    expect(auth.expireSession).toHaveBeenCalledTimes(1);
    expect(showErrorToast).not.toHaveBeenCalled();
  });
});
