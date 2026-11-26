import { useId } from "react";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseButton } from "@/components/shared/BaseButton";
import { CardItem } from "@/components/board/CardItem";
import { useAuth } from "@/context/AuthContext";
import type { DragAndDrop } from "@/hooks/useDragAndDrop";
import { sortByOrder } from "@/lib/collections";
import type { BoardColumn } from "@/lib/boardState";
import type { Card } from "@/types/api";

export interface KanbanColumnProps {
  column: BoardColumn;
  /** The cards to show. A search filter may have removed some of the column's cards. */
  cards: Card[];
  dnd: DragAndDrop;
  canWrite: boolean;
  canManage: boolean;
  onAddCard(): void;
  onRename(): void;
  onDelete(): void;
  onOpenCard(cardId: string): void;
}

export function KanbanColumn({
  column,
  cards,
  dnd,
  canWrite,
  canManage,
  onAddCard,
  onRename,
  onDelete,
  onOpenCard,
}: KanbanColumnProps) {
  const headingId = useId();
  const { user } = useAuth();
  const isOver = dnd.overColumnId === column.id;
  const sortedCards = sortByOrder(cards);
  // BE-AZ-04: a Member may delete only a column they created. The server still decides.
  const canDelete = canManage || (canWrite && user !== null && column.created_by === user.id);

  return (
    <section
      aria-labelledby={headingId}
      data-column-id={column.id}
      className={[
        "flex w-72 shrink-0 flex-col gap-3 rounded-lg bg-gray-50 p-3",
        isOver ? "ring-2 ring-blue-500" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 id={headingId} className="min-w-0 flex-1 break-words text-lg font-semibold text-gray-900">
          {column.name}
        </h2>
        <BaseBadge color="gray">{sortedCards.length}</BaseBadge>
        {canWrite ? (
          <BaseButton variant="secondary" onClick={onRename} className="min-h-10">
            Rename
          </BaseButton>
        ) : null}
        {canDelete ? (
          <BaseButton variant="destructive" onClick={onDelete} className="min-h-10">
            Delete
          </BaseButton>
        ) : null}
      </div>
      <ul
        data-testid="column-cards"
        {...dnd.cardDropProps(column.id)}
        className="flex min-h-16 flex-col gap-2"
      >
        {sortedCards.length === 0 ? (
          <li className="rounded-md border border-dashed border-gray-300 p-3 text-center text-base text-gray-600">
            No cards
          </li>
        ) : (
          sortedCards.map((card) => (
            <CardItem
              key={card.id}
              card={card}
              assigneeName={card.assignee?.name ?? null}
              dnd={dnd}
              onOpen={() => onOpenCard(card.id)}
            />
          ))
        )}
      </ul>
      {canWrite ? (
        <BaseButton variant="secondary" onClick={onAddCard} className="min-h-10 w-full">
          Add card
        </BaseButton>
      ) : null}
    </section>
  );
}
