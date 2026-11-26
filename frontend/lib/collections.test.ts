import { describe, expect, it } from "vitest";
import { groupByBoard } from "@/lib/collections";
import type { AssignedCard } from "@/types/api";

function card(id: string, boardId: string, boardName: string): AssignedCard {
  return {
    id,
    title: `Card ${id}`,
    column_name: "To do",
    board_id: boardId,
    board_name: boardName,
    completed_at: null,
  } as AssignedCard;
}

// My tasks grouping (FE-PAGE-05): cards group by board_id, keeping the API order.
describe("groupByBoard (FE-PAGE-05)", () => {
  it("groups cards from two boards into two groups", () => {
    const groups = groupByBoard([
      card("1", "sprint", "Sprint 12"),
      card("2", "sprint", "Sprint 12"),
      card("3", "marketing", "Marketing"),
    ]);
    expect(groups.map((group) => group.board_name)).toEqual(["Sprint 12", "Marketing"]);
    expect(groups[0].cards.map((c) => c.id)).toEqual(["1", "2"]);
    expect(groups[1].cards.map((c) => c.id)).toEqual(["3"]);
  });

  it("keys groups by board_id, so two boards with the same name stay apart", () => {
    const groups = groupByBoard([card("1", "a", "Team"), card("2", "b", "Team")]);
    expect(groups.map((group) => group.board_id)).toEqual(["a", "b"]);
  });

  it("returns no groups for an empty page", () => {
    expect(groupByBoard([])).toEqual([]);
  });
});
