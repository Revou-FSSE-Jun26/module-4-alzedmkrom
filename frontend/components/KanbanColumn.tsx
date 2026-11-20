import { useId } from 'react';
import { BaseBadge } from '@/components/shared/BaseBadge';
import { BaseButton } from '@/components/shared/BaseButton';
import { CardItem } from '@/components/CardItem';
import type { DragAndDrop } from '@/hooks/useDragAndDrop';
import { sortByOrder } from '@/lib/collections';
import type { Card, ColumnWithCards, Member } from '@/lib/types';

export interface KanbanColumnProps {
  column: ColumnWithCards;
  // The cards to show. A search filter may have removed some of the column's cards.
  cards: Card[];
  memberById: ReadonlyMap<string, Member>;
  dnd: DragAndDrop;
  onAddCard(): void;
  onRename(): void;
  onDelete(): void;
  onOpenCard(cardId: string): void;
}

export function KanbanColumn({
  column,
  cards,
  memberById,
  dnd,
  onAddCard,
  onRename,
  onDelete,
  onOpenCard,
}: KanbanColumnProps) {
  const headingId = useId();
  const isOver = dnd.overColumnId === column.id;
  const sortedCards = sortByOrder(cards);

  return (
    <section
      aria-labelledby={headingId}
      data-column-id={column.id}
      className={[
        'flex w-72 shrink-0 flex-col gap-3 rounded-lg bg-gray-50 p-3',
        isOver ? 'ring-2 ring-blue-500' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div {...dnd.columnHandleProps(column.id)} className="flex items-center gap-2">
        <h2 id={headingId} className="min-w-0 flex-1 break-words text-base font-semibold text-gray-900">
          {column.title}
        </h2>
        <BaseBadge color="gray">{sortedCards.length}</BaseBadge>
        <BaseButton variant="secondary" onClick={onRename} className="min-h-10">
          Rename
        </BaseButton>
        <BaseButton variant="destructive" onClick={onDelete} className="min-h-10">
          Delete
        </BaseButton>
      </div>

      <ul
        data-testid="column-cards"
        {...dnd.cardDropProps(column.id)}
        className="flex min-h-16 flex-col gap-2"
      >
        {sortedCards.length === 0 ? (
          <li className="rounded-md border border-dashed border-gray-300 p-3 text-center text-sm text-gray-500">
            No cards
          </li>
        ) : (
          sortedCards.map((card) => (
            <CardItem
              key={card.id}
              card={card}
              assigneeName={
                card.assignee_id === null ? null : (memberById.get(card.assignee_id)?.name ?? null)
              }
              dnd={dnd}
              onOpen={() => onOpenCard(card.id)}
            />
          ))
        )}
      </ul>

      <BaseButton variant="secondary" onClick={onAddCard} className="min-h-10 w-full">
        Add card
      </BaseButton>
    </section>
  );
}
