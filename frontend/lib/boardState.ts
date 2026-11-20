// Board state for the board detail page. The reducer is pure: every action
// returns a new state object and never mutates its input. Columns and cards
// are kept sorted by `order` ascending.

import { sortByOrder } from "./collections";
import type { BoardDetail, Card, Column, ColumnWithCards, Role } from "./types";

export interface BoardState {
  board: { id: string; name: string; role: Role; owner_id: string };
  columns: ColumnWithCards[];
}

export type BoardAction =
  | { type: "board/renamed"; name: string }
  | { type: "column/added"; column: ColumnWithCards }
  | { type: "column/renamed"; column: Column }
  | { type: "column/removed"; columnId: string }
  | { type: "column/moved"; columnId: string; order: number }
  | { type: "columns/orders-applied"; columns: Column[] }
  | { type: "card/added"; columnId: string; card: Card }
  | { type: "card/replaced"; card: Card }
  | { type: "card/removed"; cardId: string }
  | { type: "card/moved"; cardId: string; toColumnId: string; order: number }
  | { type: "cards/orders-applied"; columnId: string; orders: { id: string; order: number }[] }
  | { type: "state/restored"; snapshot: BoardState };

export function initBoardState(detail: BoardDetail): BoardState {
  return {
    board: { id: detail.id, name: detail.name, role: detail.role, owner_id: detail.owner_id },
    columns: sortByOrder(detail.columns).map((column) => ({
      ...column,
      cards: sortByOrder(column.cards),
    })),
  };
}

export function boardReducer(state: BoardState, action: BoardAction): BoardState {
  switch (action.type) {
    case "board/renamed":
      return { ...state, board: { ...state.board, name: action.name } };

    case "column/added":
      return {
        ...state,
        columns: sortByOrder([...state.columns, { ...action.column, cards: [] }]),
      };

    case "column/renamed":
      return {
        ...state,
        columns: state.columns.map((column) =>
          column.id === action.column.id
            ? { ...column, title: action.column.title, updated_at: action.column.updated_at }
            : column,
        ),
      };

    case "column/removed":
      return {
        ...state,
        columns: state.columns.filter((column) => column.id !== action.columnId),
      };

    case "column/moved":
      return {
        ...state,
        columns: sortByOrder(
          state.columns.map((column) =>
            column.id === action.columnId ? { ...column, order: action.order } : column,
          ),
        ),
      };

    case "columns/orders-applied": {
      const orders = new Map(action.columns.map((column) => [column.id, column.order]));
      return {
        ...state,
        columns: sortByOrder(
          state.columns.map((column) => {
            const order = orders.get(column.id);
            return order === undefined ? column : { ...column, order };
          }),
        ),
      };
    }

    case "card/added":
      return {
        ...state,
        columns: mapColumn(state, action.columnId, (column) => ({
          ...column,
          cards: sortByOrder([...column.cards, action.card]),
        })),
      };

    case "card/replaced":
      return {
        ...state,
        columns: state.columns.map((column) => ({
          ...column,
          cards: column.cards.map((card) => (card.id === action.card.id ? action.card : card)),
        })),
      };

    case "card/removed":
      return {
        ...state,
        columns: state.columns.map((column) => ({
          ...column,
          cards: column.cards.filter((card) => card.id !== action.cardId),
        })),
      };

    case "card/moved": {
      const found = findCard(state, action.cardId);
      const targetExists = state.columns.some((column) => column.id === action.toColumnId);
      if (found === null || !targetExists) {
        return { ...state };
      }
      const movedCard: Card = { ...found.card, order: action.order };
      return {
        ...state,
        columns: state.columns.map((column) => {
          const remaining = column.cards.filter((card) => card.id !== action.cardId);
          const cards = column.id === action.toColumnId ? [...remaining, movedCard] : remaining;
          return { ...column, cards: sortByOrder(cards) };
        }),
      };
    }

    case "cards/orders-applied": {
      const orders = new Map(action.orders.map((entry) => [entry.id, entry.order]));
      return {
        ...state,
        columns: mapColumn(state, action.columnId, (column) => ({
          ...column,
          cards: sortByOrder(
            column.cards.map((card) => {
              const order = orders.get(card.id);
              return order === undefined ? card : { ...card, order };
            }),
          ),
        })),
      };
    }

    case "state/restored":
      return action.snapshot;
  }
}

export function findCard(
  state: BoardState,
  cardId: string,
): { card: Card; columnId: string } | null {
  for (const column of state.columns) {
    const card = column.cards.find((item) => item.id === cardId);
    if (card !== undefined) {
      return { card, columnId: column.id };
    }
  }
  return null;
}

// Cards whose id is in `searchIds`, in their original order. `null` means no
// search is active, so every card is returned.
export function visibleCards(
  cards: readonly Card[],
  searchIds: ReadonlySet<string> | null,
): Card[] {
  if (searchIds === null) {
    return [...cards];
  }
  return cards.filter((card) => searchIds.has(card.id));
}

function mapColumn(
  state: BoardState,
  columnId: string,
  update: (column: ColumnWithCards) => ColumnWithCards,
): ColumnWithCards[] {
  return state.columns.map((column) => (column.id === columnId ? update(column) : column));
}
