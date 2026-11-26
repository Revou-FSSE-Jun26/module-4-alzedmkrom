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
import { dropIndex, orderForIndex } from "@/lib/ordering";
import type { CardMoveResult } from "@/types/api";

/** The drag data type for cards (FE-DND-01). Other drag payloads are ignored. */
export const CARD_DRAG_TYPE = "application/x-revotask-card";

type DragHandler = (event: DragEvent<HTMLElement>) => void;

export interface UseDragAndDropArgs {
  state: BoardState;
  dispatch: Dispatch<BoardAction>;
  /** True for Member and Admin only (FE-DND-04). */
  canWrite: boolean;
  /** True while a search filter is active (decision F7). */
  disabled?: boolean;
}

export interface DragAndDrop {
  /** Card currently being dragged, if any. */
  draggingCardId: string | null;
  /** Column highlighted as the drop target. */
  overColumnId: string | null;
  /** Cards with a move request in flight. Their drag is disabled (FE-DND-04). */
  pendingCardIds: ReadonlySet<string>;
  /**
   * Moves a card and sends the request. Shared by drag and drop and by the "Move to column"
   * select (FE-DND-05). `position` is the insertion index, or "end".
   */
  moveCard(cardId: string, targetColumnId: string, position: number | "end"): Promise<void>;
  cardDragProps(cardId: string): {
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
}

// Native HTML5 drag and drop for cards (FE-DND-01). The hook applies the move to local state
// first (FE-DND-03). A failed request restores the snapshot taken before the move, then shows
// the error through useErrorHandler.
export function useDragAndDrop({
  state,
  dispatch,
  canWrite,
  disabled = false,
}: UseDragAndDropArgs): DragAndDrop {
  const api = useApi();
  const handleError = useErrorHandler();

  // The snapshot used for rollback is the state of the last committed render.
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const [draggingCardId, setDraggingCardId] = useState<string | null>(null);
  const [overColumnId, setOverColumnId] = useState<string | null>(null);
  const [pendingCardIds, setPendingCardIds] = useState<ReadonlySet<string>>(new Set());

  const dragEnabled = canWrite && !disabled;

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

      // A drop that keeps the card in place is not sent (FE-DND-04).
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
      setPendingCardIds((current) => new Set(current).add(cardId));
      try {
        const result = await api.patch<CardMoveResult>(`/api/cards/${cardId}/position`, {
          column_id: targetColumnId,
          order,
        });
        if (result.rebalanced) {
          dispatch({
            type: "cards/orders-applied",
            columnId: targetColumnId,
            orders: result.siblings,
          });
        }
      } catch (error) {
        dispatch({ type: "state/restored", snapshot });
        handleError(error);
      } finally {
        setPendingCardIds((current) => {
          const next = new Set(current);
          next.delete(cardId);
          return next;
        });
      }
    },
    [api, dispatch, handleError],
  );

  function cardDragProps(cardId: string) {
    const draggable = dragEnabled && !pendingCardIds.has(cardId);
    return {
      draggable,
      onDragStart(event: DragEvent<HTMLElement>) {
        if (!draggable) {
          event.preventDefault();
          return;
        }
        event.dataTransfer.setData(CARD_DRAG_TYPE, cardId);
        event.dataTransfer.effectAllowed = "move";
        setDraggingCardId(cardId);
      },
      onDragEnd() {
        setDraggingCardId(null);
        setOverColumnId(null);
      },
    };
  }

  function cardDropProps(columnId: string) {
    const accept: DragHandler = (event) => {
      if (!dragEnabled || !event.dataTransfer.types.includes(CARD_DRAG_TYPE)) {
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
        setOverColumnId(null);
        setDraggingCardId(null);
        if (!dragEnabled || !event.dataTransfer.types.includes(CARD_DRAG_TYPE)) {
          return;
        }
        event.preventDefault();
        const cardId = event.dataTransfer.getData(CARD_DRAG_TYPE);
        // Only ids that belong to this board are accepted (ignore foreign payloads).
        if (cardId === "" || findCard(stateRef.current, cardId) === null) {
          return;
        }
        const index = dropIndex(cardMidpoints(event.currentTarget, cardId), event.clientY);
        void moveCard(cardId, columnId, index);
      },
    };
  }

  return {
    draggingCardId,
    overColumnId,
    pendingCardIds,
    moveCard,
    cardDragProps,
    cardDropProps,
  };
}

// Vertical midpoints of the cards in a list, skipping the dragged card. The DOM order is the
// `order` order, so the result is sorted ascending.
function cardMidpoints(container: HTMLElement, excludedId: string): number[] {
  return Array.from(container.querySelectorAll<HTMLElement>("[data-card-id]"))
    .filter((element) => element.dataset.cardId !== excludedId)
    .map((element) => {
      const rect = element.getBoundingClientRect();
      return (rect.top + rect.bottom) / 2;
    });
}
