import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useEffect, useReducer } from "react";
import { useDragAndDrop, type DragAndDrop } from "@/hooks/useDragAndDrop";
import { boardReducer, initBoardState } from "@/lib/boardState";
import { ApiError } from "@/lib/errors";
import type { BoardDetail, Card, Column } from "@/types/api";

const apiMock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
const handleErrorMock = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/useApi", () => ({ useApi: () => apiMock }));
vi.mock("@/hooks/useErrorHandler", () => ({ useErrorHandler: () => handleErrorMock }));

const STAMP = "2026-01-01T00:00:00Z";

function card(id: string, title: string, columnId: string, order: number): Card {
  return {
    id,
    board_id: "b1",
    column_id: columnId,
    title,
    description: null,
    assignee_id: null,
    assignee: null,
    due_date: null,
    order,
    completed_at: null,
    created_by: "u1",
    created_at: STAMP,
  };
}

function column(id: string, name: string, order: number, cards: Card[]): Column & { cards: { items: Card[] } } {
  return {
    id,
    board_id: "b1",
    name,
    order,
    is_done: false,
    created_by: "u1",
    created_at: STAMP,
    updated_at: STAMP,
    cards: { items: cards },
  };
}

// Todo: c1 (1024), c2 (2048). Done: c3 (1024).
function boardFixture(): BoardDetail {
  return {
    id: "b1",
    name: "Sprint",
    is_public: true,
    created_by: "u1",
    created_at: STAMP,
    updated_at: STAMP,
    my_role: "member",
    columns: {
      items: [
        column("col1", "Todo", 1024, [card("c1", "Write", "col1", 1024), card("c2", "Review", "col1", 2048)]),
        column("col2", "Done", 2048, [card("c3", "Ship", "col2", 1024)]),
      ],
    },
  };
}

function Harness({ canWrite, onReady }: { canWrite: boolean; onReady: (dnd: DragAndDrop) => void }) {
  const [state, dispatch] = useReducer(boardReducer, boardFixture(), initBoardState);
  const dnd = useDragAndDrop({ state, dispatch, canWrite });
  useEffect(() => {
    onReady(dnd);
  });
  return (
    <div>
      {state.columns.map((col) => (
        <div key={col.id} data-testid={col.id}>
          {col.cards.map((c) => (
            <span key={c.id} data-testid={c.id}>
              {`${c.title}:${c.order}`}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}

function renderHarness(canWrite = true) {
  let current: DragAndDrop | null = null;
  render(<Harness canWrite={canWrite} onReady={(value) => (current = value)} />);
  const dnd = (): DragAndDrop => {
    if (current === null) {
      throw new Error("harness not rendered");
    }
    return current;
  };
  return { dnd };
}

describe("useDragAndDrop (FE-DND-01..04)", () => {
  beforeEach(() => {
    apiMock.patch.mockReset();
    handleErrorMock.mockReset();
  });

  it("applies the move to local state before the request finishes (optimistic update)", async () => {
    apiMock.patch.mockReturnValue(new Promise(() => undefined));
    const { dnd } = renderHarness();
    await act(async () => {
      void dnd().moveCard("c1", "col2", "end");
    });
    // c1 goes after c3 (1024), so its order is computeOrder(1024, null) = 2048 (BE-ORD-01).
    expect(screen.getByTestId("c1").textContent).toBe("Write:2048");
    expect(screen.getByTestId("col2").textContent).toContain("Write:2048");
    expect(apiMock.patch).toHaveBeenCalledWith("/api/cards/c1/position", {
      column_id: "col2",
      order: 2048,
    });
  });

  it("restores the exact previous column and order when the request fails", async () => {
    const failure = new ApiError(422, "Invalid", "VALIDATION_ERROR", { order: ["Must be greater than 0."] });
    apiMock.patch.mockRejectedValue(failure);
    const { dnd } = renderHarness();
    await act(async () => {
      await dnd().moveCard("c1", "col2", "end");
    });
    expect(screen.getByTestId("col1").textContent).toContain("Write:1024");
    expect(screen.getByTestId("col2").textContent).not.toContain("Write");
    expect(handleErrorMock).toHaveBeenCalledWith(failure);
  });

  it("ignores a drop that keeps the card in the same position", async () => {
    const { dnd } = renderHarness();
    await act(async () => {
      await dnd().moveCard("c1", "col1", 0);
    });
    expect(apiMock.patch).not.toHaveBeenCalled();
  });

  it("applies sibling orders when the server rebalances the column", async () => {
    apiMock.patch.mockResolvedValue({
      ...card("c1", "Write", "col2", 1024),
      rebalanced: true,
      siblings: [
        { id: "c1", order: 1024 },
        { id: "c3", order: 2048 },
      ],
    });
    const { dnd } = renderHarness();
    await act(async () => {
      await dnd().moveCard("c1", "col2", "end");
    });
    expect(screen.getByTestId("c1").textContent).toBe("Write:1024");
    expect(screen.getByTestId("c3").textContent).toBe("Ship:2048");
  });

  it("does not make cards draggable for a read-only viewer", () => {
    const { dnd } = renderHarness(false);
    expect(dnd().cardDragProps("c1").draggable).toBe(false);
  });

  it("makes cards draggable for a Member", () => {
    const { dnd } = renderHarness(true);
    expect(dnd().cardDragProps("c1").draggable).toBe(true);
  });
});
