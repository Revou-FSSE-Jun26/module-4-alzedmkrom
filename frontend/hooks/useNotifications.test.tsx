import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthContext, type AuthContextValue } from "@/context/AuthContext";
import { POLL_INTERVAL_MS, useNotifications } from "@/hooks/useNotifications";
import { ApiError } from "@/lib/errors";
import type { NotificationPage } from "@/types/api";

const apiMock = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));
const handleErrorMock = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/useApi", () => ({ useApi: () => apiMock }));
vi.mock("@/hooks/useErrorHandler", () => ({ useErrorHandler: () => handleErrorMock }));

const page = (unread: number): NotificationPage => ({
  items: [
    {
      id: "n1",
      type: "card_assigned",
      message: "Card assigned to you.",
      board_id: "b1",
      is_read: false,
      created_at: "2026-01-01T00:00:00Z",
    },
  ],
  page: 1,
  per_page: 20,
  total: 1,
  pages: 1,
  unread_count: unread,
});

const auth: AuthContextValue = {
  token: "tok",
  user: null,
  updateUser: vi.fn(),
  clearSession: vi.fn(),
  logout: vi.fn(async () => undefined),
  expireSession: vi.fn(async () => undefined),
};

function wrapper({ children }: { children: ReactNode }) {
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

function setHidden(hidden: boolean) {
  Object.defineProperty(document, "hidden", { value: hidden, configurable: true });
}

describe("useNotifications (FE-NTF-01)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    apiMock.get.mockReset();
    apiMock.get.mockResolvedValue(page(3));
    handleErrorMock.mockReset();
    setHidden(false);
  });

  afterEach(() => {
    vi.useRealTimers();
    setHidden(false);
  });

  it("polls every 30 seconds and polls once on mount", async () => {
    expect(POLL_INTERVAL_MS).toBe(30_000);
    renderHook(() => useNotifications(), { wrapper });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(apiMock.get).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(29_999);
    });
    expect(apiMock.get).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(apiMock.get).toHaveBeenCalledTimes(2);
  });

  it("takes unreadCount from the API, not from the page length", async () => {
    apiMock.get.mockResolvedValue(page(42));
    const { result } = renderHook(() => useNotifications(), { wrapper });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.unreadCount).toBe(42);
  });

  it("clears its timer on unmount", async () => {
    const { unmount } = renderHook(() => useNotifications(), { wrapper });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    unmount();
    apiMock.get.mockClear();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(120_000);
    });
    expect(apiMock.get).not.toHaveBeenCalled();
  });

  it("does not start an overlapping request while one is pending", async () => {
    apiMock.get.mockReturnValue(new Promise(() => undefined));
    renderHook(() => useNotifications(), { wrapper });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(90_000);
    });
    expect(apiMock.get).toHaveBeenCalledTimes(1);
  });

  it("pauses while the document is hidden and refreshes once when it is visible again", async () => {
    renderHook(() => useNotifications(), { wrapper });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    setHidden(true);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(apiMock.get).toHaveBeenCalledTimes(1);
    setHidden(false);
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(apiMock.get).toHaveBeenCalledTimes(2);
  });

  it("stops polling after a 401 and hands the error to the error handler", async () => {
    const expired = new ApiError(401, "Log in again.", "UNAUTHENTICATED");
    apiMock.get.mockRejectedValue(expired);
    renderHook(() => useNotifications(), { wrapper });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(handleErrorMock).toHaveBeenCalledWith(expired);
    apiMock.get.mockClear();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(120_000);
    });
    expect(apiMock.get).not.toHaveBeenCalled();
  });
});
