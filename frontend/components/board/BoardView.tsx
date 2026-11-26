"use client";

import { useMemo, useReducer, useState } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { ConfirmModal } from "@/components/shared/ConfirmModal";
import { BoardHeader } from "@/components/board/BoardHeader";
import { CardDetailModal } from "@/components/board/CardDetailModal";
import { CardFormModal } from "@/components/board/CardFormModal";
import { CardSearch } from "@/components/board/CardSearch";
import { ColumnFormModal } from "@/components/board/ColumnFormModal";
import { KanbanColumn } from "@/components/board/KanbanColumn";
import { ReadOnlyNotice } from "@/components/ReadOnlyNotice";
import { useApi } from "@/hooks/useApi";
import { useDragAndDrop } from "@/hooks/useDragAndDrop";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { boardReducer, findCard, initBoardState, visibleCards, type BoardColumn } from "@/lib/boardState";
import { rolesFor } from "@/lib/roles";
import type { BoardDetail, Column, Member } from "@/types/api";

// Which dialog is open on the board. `null` means none.
type ModalState =
  | null
  | { kind: "addColumn" }
  | { kind: "renameColumn"; columnId: string }
  | { kind: "deleteColumn"; columnId: string }
  | { kind: "addCard"; columnId: string };

export interface BoardViewProps {
  initialBoard: BoardDetail;
  members: Member[];
}

// The interactive board: columns, cards, search, drag and drop, and the dialogs that change
// them. Write controls appear only for Members and Admins (FE-ROLE-01, FE-ROLE-02).
export function BoardView({ initialBoard, members }: BoardViewProps) {
  const [state, dispatch] = useReducer(boardReducer, initialBoard, initBoardState);
  // The search term from CardSearch. Matching runs in the browser (CardSearch.tsx).
  const [searchTerm, setSearchTerm] = useState("");
  const searchIds = useMemo(() => matchingCardIds(state.columns, searchTerm), [state.columns, searchTerm]);
  const [modal, setModal] = useState<ModalState>(null);
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  const [deletePending, setDeletePending] = useState(false);
  const api = useApi();
  const handleError = useErrorHandler();

  const roles = rolesFor(state.board.my_role);

  // Dragging is off while a search filter is active (decision F7).
  const dnd = useDragAndDrop({
    state,
    dispatch,
    canWrite: roles.canWrite,
    disabled: searchIds !== null,
  });

  const selected = selectedCardId === null ? null : findCard(state, selectedCardId);
  // The card modal closes when its card no longer exists, for example after a delete.
  // This runs during render, not in an effect, to avoid a cascading render.
  if (selectedCardId !== null && selected === null) {
    setSelectedCardId(null);
  }

  const columnsWithShownCards = state.columns.map((column) => ({
    column,
    cards: visibleCards(column.cards, searchIds),
  }));
  const noMatches =
    searchIds !== null && columnsWithShownCards.every((entry) => entry.cards.length === 0);

  const renameTarget =
    modal?.kind === "renameColumn"
      ? state.columns.find((column) => column.id === modal.columnId)
      : undefined;
  const deleteTarget =
    modal?.kind === "deleteColumn"
      ? state.columns.find((column) => column.id === modal.columnId)
      : undefined;
  const addCardColumnId = modal?.kind === "addCard" ? modal.columnId : null;

  function closeModal() {
    setModal(null);
  }

  function handleColumnSaved(saved: Column) {
    if (modal?.kind === "renameColumn") {
      dispatch({ type: "column/renamed", column: saved });
    } else {
      dispatch({ type: "column/added", column: saved });
    }
  }

  async function confirmDeleteColumn(columnId: string) {
    if (deletePending) {
      return;
    }
    setDeletePending(true);
    try {
      await api.delete<void>(`/api/columns/${columnId}`);
      setDeletePending(false);
      dispatch({ type: "column/removed", columnId });
      closeModal();
    } catch (caught) {
      // The confirmation stays open so the user can retry or cancel. The board is unchanged.
      setDeletePending(false);
      handleError(caught);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <BoardHeader
        board={state.board}
        onRenamed={(name) => dispatch({ type: "board/renamed", name })}
      />
      <ReadOnlyNotice role={state.board.my_role} />
      <div className="flex flex-wrap items-center gap-3">
        <CardSearch onTermChange={setSearchTerm} />
        {roles.canWrite ? (
          <BaseButton onClick={() => setModal({ kind: "addColumn" })}>Add column</BaseButton>
        ) : null}
      </div>
      {noMatches ? (
        <p role="status" className="text-base text-gray-600">
          No cards match your search
        </p>
      ) : null}
      {state.columns.length === 0 ? (
        <p className="text-base text-gray-600">
          {roles.canWrite ? "No columns yet. Add the first column to start." : "No columns yet."}
        </p>
      ) : null}
      <div className="flex gap-4 overflow-x-auto">
        {columnsWithShownCards.map(({ column, cards }) => (
          <KanbanColumn
            key={column.id}
            column={column}
            cards={cards}
            dnd={dnd}
            canWrite={roles.canWrite}
            canManage={roles.canManage}
            onAddCard={() => setModal({ kind: "addCard", columnId: column.id })}
            onRename={() => setModal({ kind: "renameColumn", columnId: column.id })}
            onDelete={() => setModal({ kind: "deleteColumn", columnId: column.id })}
            onOpenCard={(cardId) => setSelectedCardId(cardId)}
          />
        ))}
      </div>
      <ColumnFormModal
        mode={modal?.kind === "renameColumn" ? "rename" : "create"}
        open={modal?.kind === "addColumn" || modal?.kind === "renameColumn"}
        boardId={state.board.id}
        column={renameTarget}
        onClose={closeModal}
        onSaved={handleColumnSaved}
      />
      <CardFormModal
        open={addCardColumnId !== null}
        columnId={addCardColumnId ?? ""}
        members={members}
        onClose={closeModal}
        onCreated={(card) => {
          if (addCardColumnId !== null) {
            dispatch({ type: "card/added", columnId: addCardColumnId, card });
          }
        }}
      />
      <ConfirmModal
        open={modal?.kind === "deleteColumn"}
        title="Delete column"
        message={
          deleteTarget === undefined
            ? "Delete this column and all its cards? This cannot be undone."
            : `Delete "${deleteTarget.name}" and all its cards? This cannot be undone.`
        }
        confirmLabel="Delete"
        pending={deletePending}
        onConfirm={() => {
          if (modal?.kind === "deleteColumn") {
            void confirmDeleteColumn(modal.columnId);
          }
        }}
        onCancel={closeModal}
      />
      {selected !== null ? (
        <CardDetailModal
          card={selected.card}
          columnId={selected.columnId}
          columns={state.columns}
          members={members}
          role={state.board.my_role}
          dnd={dnd}
          onClose={() => setSelectedCardId(null)}
          onSaved={(card) => dispatch({ type: "card/replaced", card })}
          onDeleted={(cardId) => dispatch({ type: "card/removed", cardId })}
        />
      ) : null}
    </div>
  );
}

// Ids of the cards whose title or description contains the term, ignoring case. Null means no
// search is active, so every card is shown. Dragging is disabled while a search is active (F7).
function matchingCardIds(
  columns: readonly BoardColumn[],
  term: string,
): ReadonlySet<string> | null {
  if (term === "") {
    return null;
  }
  const needle = term.toLocaleLowerCase();
  const ids = new Set<string>();
  for (const column of columns) {
    for (const card of column.cards) {
      const haystack = `${card.title}\n${card.description ?? ""}`.toLocaleLowerCase();
      if (haystack.includes(needle)) {
        ids.add(card.id);
      }
    }
  }
  return ids;
}