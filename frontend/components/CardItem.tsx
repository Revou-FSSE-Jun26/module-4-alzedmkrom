import type { KeyboardEvent } from 'react';
import { BaseBadge } from '@/components/shared/BaseBadge';
import type { DragAndDrop } from '@/hooks/useDragAndDrop';
import type { Card } from '@/lib/types';

export interface CardItemProps {
  card: Card;
  assigneeName: string | null;
  dnd: DragAndDrop;
  onOpen(): void;
}

// A div with role="button" instead of a native button, because the element is
// draggable and native buttons are reserved for BaseButton.
export function CardItem({ card, assigneeName, dnd, onOpen }: CardItemProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    // Enter pressed on a control nested inside the card must not open the modal.
    if (event.key === 'Enter' && event.target === event.currentTarget) {
      onOpen();
    }
  }

  return (
    <li>
      <div
        role="button"
        tabIndex={0}
        data-testid="card"
        data-card-id={card.id}
        {...dnd.cardDragProps(card.id)}
        onClick={() => onOpen()}
        onKeyDown={handleKeyDown}
      >
        <p>{card.title}</p>
        {card.completed_at !== null ? <BaseBadge color="green">Completed</BaseBadge> : null}
        {card.assignee_id !== null && assigneeName !== null ? <p>{assigneeName}</p> : null}
      </div>
    </li>
  );
}
