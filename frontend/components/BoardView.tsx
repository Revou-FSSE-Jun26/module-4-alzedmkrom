"use client";

import { useMemo, useReducer, useState } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { ConfirmModal } from "@/components/shared/ConfirmModal";
import { BoardHeader } from "@/components/BoardHeader";
import { CardDetailModal } from "@/components/CardDetailModal";
import { CardFormModal } from "@/components/CardFormModal";
import { CardSearch } from "@/components/CardSearch";
import { ColumnFormModal } from "@/components/ColumnFormModal";
import { KanbanColumn } from "@/components/KanbanColumn";
import { useApi } from "@/hooks/useApi";
import { useDragAndDrop } from "@/hooks/useDragAndDrop";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import {
  boardReducer,
  findCard,
  initBoardState,
  visibleCards,
} from "@/lib/boardState";
import type { BoardDetail, Column, DeletedId, Member } from "@/lib/types";

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

// The interactive board: columns, cards, search, drag and drop, and the dialogs
// that change them (Requirements 10.2 to 10.4, 11.3 to 11.6, 11.10, 12.9, 13.11, 15.4, 15.6).
export function BoardView({ initialBoard, members }: BoardViewProps) {
  const [state, dispatch] = useReducer(boardReducer, initialBoard, initBoardState);
  // Ids of the cards matching the search, or null when no search is active.
  const [searchIds, setSearchIds] = useState<ReadonlySet<string> | null>(null);
  const [modal, setModal] = useState<ModalState>(null);
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null);
  const [deletePending, setDeletePending] = useState(false);

  const api = useApi();
  const handleError = useErrorHandler();
  // Dragging is off while a search filter is active (decision F7).
  const dnd = useDragAndDrop({
    boardId: state.board.id,
    state,
    dispatch,
    disabled: searchIds !== null,
  });

  const memberById = useMemo(
    () => new Map(members.map((member) => [member.user_id, member])),
    [members],
  );

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
      dispatch({ type: "column/added", column: { ...saved, cards: [] } });
    }
  }

  async function confirmDeleteColumn(columnId: string) {
    if (deletePending) {
      return;
    }
    setDeletePending(true);
    try {
      await api.delete<DeletedId>(`/api/columns/${columnId}`);
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

      <div className="flex flex-wrap items-center gap-3">
        <CardSearch onResults={(ids) => setSearchIds(ids)} />
        <BaseButton onClick={() => setModal({ kind: "addColumn" })}>Add column</BaseButton>
      </div>

      {noMatches ? (
        <p role="status" className="text-sm text-gray-600">
          No cards match your search
        </p>
      ) : null}

      <div className="flex gap-4 overflow-x-auto" {...dnd.columnDropProps()}>
        {columnsWithShownCards.map(({ column, cards }) => (
          <KanbanColumn
            key={column.id}
            column={column}
            cards={cards}
            memberById={memberById}
            dnd={dnd}
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
            : `Delete "${deleteTarget.title}" and all its cards? This cannot be undone.`
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
          boardRole={state.board.role}
          dnd={dnd}
          onClose={() => setSelectedCardId(null)}
          onSaved={(card) => dispatch({ type: "card/replaced", card })}
          onDeleted={(cardId) => dispatch({ type: "card/removed", cardId })}
        />
      ) : null}
    </div>
  );
}
