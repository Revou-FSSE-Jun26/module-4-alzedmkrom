import { describe, expect, it } from "vitest";
import { loginPath, safeNextPath } from "@/lib/session";

// FE-SEC-03: only same-origin relative paths that start with a single slash are accepted.
describe("safeNextPath", () => {
  it.each([
    ["/my-tasks", "/my-tasks"],
    ["/boards/abc?x=1", "/boards/abc?x=1"],
  ])("keeps the same-origin path %s", (input, expected) => {
    expect(safeNextPath(input)).toBe(expected);
  });

  it.each([
    ["https://evil.example"],
    ["//evil.example/path"],
    ["/\\evil.example"],
    ["javascript:alert(1)"],
    ["my-tasks"],
    [""],
    [null],
    [undefined],
  ])("falls back to / for %s", (input) => {
    expect(safeNextPath(input)).toBe("/");
  });
});

describe("loginPath", () => {
  it("builds the query with URLSearchParams and a safe next value", () => {
    expect(loginPath({ next: "/profile", sessionExpired: true })).toBe(
      "/login?reason=session-expired&next=%2Fprofile",
    );
  });

  it("drops an unsafe next value", () => {
    expect(loginPath({ next: "https://evil.example" })).toBe("/login?next=%2F");
  });

  it("returns the bare login path with no options", () => {
    expect(loginPath()).toBe("/login");
  });
});
