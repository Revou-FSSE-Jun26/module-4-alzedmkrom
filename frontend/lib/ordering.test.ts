import { describe, expect, it } from "vitest";
import { computeOrder, dropIndex, MIN_GAP, ORDER_STEP, orderForIndex } from "@/lib/ordering";

// Examples follow backend.md BE-ORD-01.
describe("computeOrder (BE-ORD-01)", () => {
  it("uses the midpoint between two neighbours", () => {
    expect(computeOrder(1024.0, 2048.0)).toBe(1536.0);
  });

  it("uses next / 2 at the start of a container", () => {
    expect(computeOrder(null, 1024.0)).toBe(512.0);
  });

  it("uses previous + ORDER_STEP at the end of a container", () => {
    expect(computeOrder(2048.0, null)).toBe(3072.0);
  });

  it("uses ORDER_STEP in an empty container", () => {
    expect(computeOrder(null, null)).toBe(1024.0);
  });

  it("exposes the BE-ORD-01 constants", () => {
    expect(ORDER_STEP).toBe(1024.0);
    expect(MIN_GAP).toBe(1e-6);
  });
});

describe("orderForIndex and dropIndex", () => {
  it("places an item between the two items around its index", () => {
    expect(orderForIndex([1024.0, 2048.0], 1)).toBe(1536.0);
  });

  it("rejects an index outside the container", () => {
    expect(() => orderForIndex([1024.0], 3)).toThrow(RangeError);
  });

  it("returns the first index whose midpoint is below the pointer", () => {
    expect(dropIndex([10, 20, 30], 5)).toBe(0);
    expect(dropIndex([10, 20, 30], 25)).toBe(2);
    expect(dropIndex([10, 20, 30], 99)).toBe(3);
  });
});
