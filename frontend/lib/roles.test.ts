import { describe, expect, it } from "vitest";
import { rolesFor } from "@/lib/roles";

describe("rolesFor (FE-ROLE-01)", () => {
  it("lets only Members and Admins write", () => {
    expect(rolesFor("anonymous").canWrite).toBe(false);
    expect(rolesFor("guest").canWrite).toBe(false);
    expect(rolesFor("member").canWrite).toBe(true);
    expect(rolesFor("admin").canWrite).toBe(true);
  });

  it("lets only Admins manage", () => {
    expect(rolesFor("member").canManage).toBe(false);
    expect(rolesFor("admin").canManage).toBe(true);
  });
});
