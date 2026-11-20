"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type DragEvent,
} from "react";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { findCard, type BoardAction, type BoardState } from "@/lib/boardState";
import { sortByOrder } from "@/lib/collections";
import { dropIndex, orderForIndex } from "@/lib/order";
import type { CardMoveResult, ColumnReorderResult } from "@/lib/types";

type DragKind = "card" | "column";

interface DraggedItem {
  kind: DragKind;
  id: string;
}

type DragHandler = (event: DragEvent<HTMLElement>) => void;

export interface DragAndDrop {
  isMoving: boolean;
  draggingCardId: string | null;
  draggingColumnId: string | null;
  // The one column highlighted while a card is dragged over it (13.11).
  overColumnId: string | null;
  moveCard(cardId: string, targetColumnId: string, position: number | "end"): Promise<void>;
  moveColumn(columnId: string, position: number): Promise<void>;
  cardDragProps(cardId: string): {
    draggable: boolean;
    onDragStart: DragHandler;
    onDragEnd: DragHandler;
  };
  columnHandleProps(columnId: string): {
    draggable: boolean;
    onDragStart: DragHandler;
    onDragEnd: DragHandler;
  };
  cardDropProps(columnId: string): {
    onDragEnter: DragHandler;
    onDragOver: DragHandler;
    onDragLeave: DragHandler;
    onDrop: DragHandler;
  };
  columnDropProps(): {
    onDragOver: DragHandler;
    onDrop: DragHandler;
  };
}

export interface UseDragAndDropArgs {
  boardId: string;
  state: BoardState;
  dispatch: Dispatch<BoardAction>;
  // True while a search filter is active (F7).
  disabled?: boolean;
}

// Native HTML5 drag and drop for cards and columns. Requests are sent after
// the local state has changed. A failed request restores the snapshot taken
// before the move.
export function useDragAndDrop({
  boardId,
  state,
  dispatch,
  disabled = false,
}: UseDragAndDropArgs): DragAndDrop {
  const api = useApi();
  const handleError = useErrorHandler();

  // The snapshot used for rollback is the state of the last committed render.
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // dragover and drop cannot read dataTransfer data, so the dragged item lives here.
  const draggedRef = useRef<DraggedItem | null>(null);
  const [draggingCardId, setDraggingCardId] = useState<string | null>(null);
  const [draggingColumnId, setDraggingColumnId] = useState<string | null>(null);
  const [overColumnId, setOverColumnId] = useState<string | null>(null);
  // Counts move requests in flight, so isMoving stays true until all of them settle.
  const [pendingMoves, setPendingMoves] = useState(0);
  const isMoving = pendingMoves > 0;
  const blocked = disabled || isMoving;

  const clearDrag = useCallback(() => {
    draggedRef.current = null;
    setDraggingCardId(null);
    setDraggingColumnId(null);
    setOverColumnId(null);
  }, []);

  const moveCard = useCallback(
    async (cardId: string, targetColumnId: string, position: number | "end") => {
      const snapshot = stateRef.current;
      const source = findCard(snapshot, cardId);
      const target = snapshot.columns.find((column) => column.id === targetColumnId);
      if (source === null || target === undefined) {
        return;
      }

      const targetCards = sortByOrder(target.cards);
      const others = targetCards.filter((card) => card.id !== cardId);
      const index =
        position === "end" ? others.length : Math.min(Math.max(position, 0), others.length);

      if (source.columnId === targetColumnId) {
        const currentIndex = targetCards.findIndex((card) => card.id === cardId);
        if (index === currentIndex) {
          return;
        }
      }

      const order = orderForIndex(
        others.map((card) => card.order),
        index,
      );
      dispatch({ type: "card/moved", cardId, toColumnId: targetColumnId, order });

      setPendingMoves((count) => count + 1);
      try {
        const result = await api.patch<CardMoveResult>(`/api/cards/${cardId}/position`, {
          column_id: targetColumnId,
          order,
        });
        if (result.rebalanced) {
          dispatch({
            type: "cards/orders-applied",
            columnId: targetColumnId,
            orders: result.siblings ?? [],
          });
        }
      } catch (error) {
        dispatch({ type: "state/restored", snapshot });
        handleError(error);
      } finally {
        setPendingMoves((count) => count - 1);
      }
    },
    [api, dispatch, handleError],
  );

  const moveColumn = useCallback(
    async (columnId: string, position: number) => {
      const snapshot = stateRef.current;
      const columns = sortByOrder(snapshot.columns);
      const currentIndex = columns.findIndex((column) => column.id === columnId);
      if (currentIndex === -1) {
        return;
      }

      const others = columns.filter((column) => column.id !== columnId);
      const index = Math.min(Math.max(position, 0), others.length);
      if (index === currentIndex) {
        return;
      }

      const order = orderForIndex(
        others.map((column) => column.order),
        index,
      );
      dispatch({ type: "column/moved", columnId, order });

      setPendingMoves((count) => count + 1);
      try {
        const result = await api.patch<ColumnReorderResult>(
          `/api/boards/${boardId}/columns/reorder`,
          { column_id: columnId, order },
        );
        if (result.rebalanced) {
          dispatch({ type: "columns/orders-applied", columns: result.columns });
        }
      } catch (error) {
        dispatch({ type: "state/restored", snapshot });
        handleError(error);
      } finally {
        setPendingMoves((count) => count - 1);
      }
    },
    [api, boardId, dispatch, handleError],
  );

  function cardDragProps(cardId: string) {
    return {
      draggable: !blocked,
      onDragStart(event: DragEvent<HTMLElement>) {
        if (blocked) {
          event.preventDefault();
          return;
        }
        event.dataTransfer.setData("text/plain", cardId);
        event.dataTransfer.effectAllowed = "move";
        draggedRef.current = { kind: "card", id: cardId };
        setDraggingCardId(cardId);
      },
      onDragEnd() {
        clearDrag();
      },
    };
  }

  function columnHandleProps(columnId: string) {
    return {
      draggable: !blocked,
      onDragStart(event: DragEvent<HTMLElement>) {
        if (blocked) {
          event.preventDefault();
          return;
        }
        event.dataTransfer.setData("text/plain", columnId);
        event.dataTransfer.effectAllowed = "move";
        draggedRef.current = { kind: "column", id: columnId };
        setDraggingColumnId(columnId);
      },
      onDragEnd() {
        clearDrag();
      },
    };
  }

  function cardDropProps(columnId: string) {
    const accept: DragHandler = (event) => {
      if (draggedRef.current?.kind !== "card") {
        return;
      }
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      setOverColumnId(columnId);
    };

    return {
      onDragEnter: accept,
      onDragOver: accept,
      onDragLeave(event: DragEvent<HTMLElement>) {
        const next = event.relatedTarget;
        if (next instanceof Node && event.currentTarget.contains(next)) {
          return;
        }
        setOverColumnId((current) => (current === columnId ? null : current));
      },
      onDrop(event: DragEvent<HTMLElement>) {
        const dragged = draggedRef.current;
        if (dragged?.kind !== "card") {
          return;
        }
        event.preventDefault();
        const midpoints = cardMidpoints(event.currentTarget, dragged.id);
        const index = dropIndex(midpoints, event.clientY);
        clearDrag();
        void moveCard(dragged.id, columnId, index);
      },
    };
  }

  function columnDropProps() {
    return {
      onDragOver(event: DragEvent<HTMLElement>) {
        const dragged = draggedRef.current;
        if (dragged === null) {
          return;
        }
        if (dragged.kind === "column") {
          event.preventDefault();
          event.dataTransfer.dropEffect = "move";
          return;
        }
        // A card over a gap between columns is not a valid target, so the
        // highlight moves to the column under the pointer, or to none.
        setOverColumnId(columnIdOf(event.target));
      },
      onDrop(event: DragEvent<HTMLElement>) {
        const dragged = draggedRef.current;
        if (dragged?.kind !== "column") {
          return;
        }
        event.preventDefault();
        const midpoints = horizontalMidpoints(event.currentTarget, dragged.id);
        const index = dropIndex(midpoints, event.clientX);
        clearDrag();
        void moveColumn(dragged.id, index);
      },
    };
  }

  return {
    isMoving,
    draggingCardId,
    draggingColumnId,
    overColumnId,
    moveCard,
    moveColumn,
    cardDragProps,
    columnHandleProps,
    cardDropProps,
    columnDropProps,
  };
}

function columnIdOf(target: EventTarget | null): string | null {
  if (!(target instanceof Element)) {
    return null;
  }
  const column = target.closest("[data-column-id]");
  return column instanceof HTMLElement ? (column.dataset.columnId ?? null) : null;
}

// Vertical midpoints of the cards in a list, skipping the dragged card.
// The DOM order is the `order` order, so the result is sorted ascending.
function cardMidpoints(container: HTMLElement, excludedId: string): number[] {
  return Array.from(container.querySelectorAll<HTMLElement>("[data-card-id]"))
    .filter((element) => element.dataset.cardId !== excludedId)
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return (rect.top + rect.bottom) / 2;
    });
}

// Horizontal midpoints of the columns, skipping the dragged column.
function horizontalMidpoints(container: HTMLElement, excludedId: string): number[] {
  return Array.from(container.querySelectorAll<HTMLElement>("[data-column-id]"))
    .filter((element) => element.dataset.columnId !== excludedId)
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return (rect.left + rect.right) / 2;
    });
}
