import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { KanbanColumn } from "@/components/board/KanbanColumn";
import { ReadOnlyNotice } from "@/components/ReadOnlyNotice";
import type { DragAndDrop } from "@/hooks/useDragAndDrop";
import { rolesFor } from "@/lib/roles";
import { DEFAULT_TEST_USER, renderWithAuth } from "@/__tests__/helpers/renderWithAuth";
import type { BoardColumn } from "@/lib/boardState";
import type { BoardRole } from "@/types/api";

// Minimal stand-in for the drag hook. Rendering does not start any drag.
const dnd = {
  draggingCardId: null,
  overColumnId: null,
  pendingCardIds: new Set<string>(),
  moveCard: vi.fn(),
  cardDragProps: () => ({ draggable: false, onDragStart: () => undefined, onDragEnd: () => undefined }),
  cardDropProps: () => ({
    onDragEnter: () => undefined,
    onDragOver: () => undefined,
    onDragLeave: () => undefined,
    onDrop: () => undefined,
  }),
} as unknown as DragAndDrop;

function column(createdBy: string | null): BoardColumn {
  return {
    id: "col1",
    board_id: "b1",
    name: "Todo",
    order: 1024,
    is_done: false,
    created_by: createdBy,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    cards: [],
  };
}

function renderColumn(role: BoardRole, createdBy: string | null) {
  const flags = rolesFor(role);
  return renderWithAuth(
    <KanbanColumn
      column={column(createdBy)}
      cards={[]}
      dnd={dnd}
      canWrite={flags.canWrite}
      canManage={flags.canManage}
      onAddCard={() => undefined}
      onRename={() => undefined}
      onDelete={() => undefined}
      onOpenCard={() => undefined}
    />,
  );
}

describe("role-aware column controls (FE-ROLE-01, FE-ROLE-02)", () => {
  it("Guest sees no write controls", () => {
    renderColumn("guest", null);
    expect(screen.queryByRole("button", { name: "Add card" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Rename" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });

  it("Member sees Add card and Rename, but not Delete on another member's column", () => {
    renderColumn("member", "someone-else");
    expect(screen.getByRole("button", { name: "Add card" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rename" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  });

  it("Member sees Delete on a column they created (BE-AZ-04)", () => {
    renderColumn("member", DEFAULT_TEST_USER.id);
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("Admin sees Delete on any column", () => {
    renderColumn("admin", "someone-else");
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });
});

describe("ReadOnlyNotice (FE-ROLE-02)", () => {
  it("Anonymous visitors see the log-in prompt", () => {
    renderWithAuth(<ReadOnlyNotice role="anonymous" />, { token: null, user: null });
    expect(screen.getByRole("link", { name: "Log in to contribute" })).toHaveAttribute("href", "/login");
  });

  it("Guests see the read-only note", () => {
    renderWithAuth(<ReadOnlyNotice role="guest" />);
    expect(
      screen.getByText("You have read-only access. Ask a board admin to add you as a member."),
    ).toBeInTheDocument();
  });

  it("Members and Admins see no notice", () => {
    const { container } = renderWithAuth(<ReadOnlyNotice role="member" />);
    expect(container).toBeEmptyDOMElement();
  });
});
