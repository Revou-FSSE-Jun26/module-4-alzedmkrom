// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient, resolveBaseUrl } from "@/lib/apiClient";

// Server-side behaviour: API_BASE_URL is read, and every request is sent with cache "no-store" (FE-API-02).
describe("apiClient (server environment)", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubEnv("API_BASE_URL", "http://server.test");
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://public.test");
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("reads API_BASE_URL on the server, not NEXT_PUBLIC_API_BASE_URL", () => {
    expect(resolveBaseUrl()).toBe("http://server.test");
  });

  it("sends the request with cache no-store", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ id: "1" }), { status: 200 }));
    await apiClient.get("/api/boards/1", { token: "t" });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://server.test/api/boards/1");
    expect(init.cache).toBe("no-store");
    expect(new Headers(init.headers).get("authorization")).toBe("Bearer t");
  });

  it("throws a clear error when API_BASE_URL is missing on the server", () => {
    vi.stubEnv("API_BASE_URL", "");
    expect(() => resolveBaseUrl()).toThrow("API_BASE_URL is not set");
  });
});
