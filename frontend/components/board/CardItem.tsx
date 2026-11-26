import type { KeyboardEvent } from "react";
import { BaseBadge } from "@/components/shared/BaseBadge";
import type { DragAndDrop } from "@/hooks/useDragAndDrop";
import type { Card } from "@/types/api";

export interface CardItemProps {
  card: Card;
  assigneeName: string | null;
  dnd: DragAndDrop;
  onOpen(): void;
}

// A div with role="button" instead of a native button, because the element is draggable and
// native buttons are reserved for BaseButton (FE-UI-01).
export function CardItem({ card, assigneeName, dnd, onOpen }: CardItemProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" && event.target === event.currentTarget) {
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
        className="flex cursor-pointer flex-col gap-2 rounded-md border border-gray-200 bg-white p-3 hover:border-gray-400"
      >
        <p className="text-base font-semibold text-gray-900">{card.title}</p>
        <div className="flex flex-wrap items-center gap-2">
          {card.completed_at !== null ? <BaseBadge color="green">Completed</BaseBadge> : null}
          {card.due_date !== null ? (
            <BaseBadge color="yellow">Due {card.due_date}</BaseBadge>
          ) : null}
        </div>
        {assigneeName !== null ? <p className="text-base text-gray-600">{assigneeName}</p> : null}
      </div>
    </li>
  );
}
