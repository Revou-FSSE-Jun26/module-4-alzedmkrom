// API payload types. They mirror the backend JSON exactly, with snake_case
// names and no mapping layer (FE-STR-04). Shapes come from backend.md BE-ERR-03,
// BE-ERR-05, BE-SVC-04, BE-ANL-01, BE-NTF-03, and the backend Marshmallow schemas.

/** BE-ERR-01 error body. */
export interface ErrorBody {
  error: {
    code: string
    message: string
    details: Record<string, string[]> | null
  }
}

/** BE-ERR-03 pagination envelope. */
export interface Paginated<T> {
  items: T[]
  page: number
  per_page: number
  total: number
  pages: number
}

/** BE-ERR-05 non-paginated list wrapper. */
export interface Items<T> {
  items: T[]
}

/** Public user shape (BE-VAL-04). */
export interface PublicUser {
  id: string
  name: string
}

/** Own profile, from GET /api/users/me (BE-VAL-04). */
export interface User extends PublicUser {
  email: string
  created_at: string
  updated_at: string
}

/** POST /api/auth/login. The body has no user (BE-AUTH-02). */
export interface LoginResponse {
  access_token: string
  token_type: 'Bearer'
  expires_in: number
}

/** Board role for the viewer (BE-SVC-04). */
export type BoardRole = 'anonymous' | 'guest' | 'member' | 'admin'

export interface Board {
  id: string
  name: string
  is_public: boolean
  created_by: string | null
  created_at: string
  updated_at: string
  my_role: BoardRole
}

export interface Column {
  id: string
  board_id: string
  name: string
  order: number
  is_done: boolean
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface Card {
  id: string
  board_id: string
  column_id: string
  title: string
  description: string | null
  assignee_id: string | null
  assignee: PublicUser | null
  due_date: string | null
  order: number
  completed_at: string | null
  created_by: string | null
  created_at: string
}

/** PATCH /api/boards/<id>/columns/reorder response (BE-ORD-02). */
export interface ColumnReorderResult extends Column {
  rebalanced: boolean
  siblings: { id: string; order: number }[]
}

export interface ColumnWithCards extends Column {
  cards: Items<Card>
}

/** GET /api/boards/<id>. Columns and cards are nested `{items}` lists. */
export interface BoardDetail extends Board {
  columns: Items<ColumnWithCards>
}

/** Membership role stored on the board (DB-MEM-01). */
export type MemberRole = 'member' | 'admin'

export interface Member {
  user_id: string
  name: string
  email: string | null
  role: MemberRole
  created_at: string
}

export interface Comment {
  id: string
  content: string
  author: PublicUser | null
  created_at: string
  updated_at: string
}

export type NotificationType =
  | 'card_assigned'
  | 'comment_added'
  | 'card_created'
  | 'card_moved'
  | 'card_deleted'
  | 'column_deleted'
  | 'board_deleted'
  | 'member_added'
  | 'member_role_changed'
  | 'member_removed'

export interface Notification {
  id: string
  type: NotificationType
  message: string
  board_id: string | null
  is_read: boolean
  created_at: string
}

/** GET /api/notifications (BE-NTF-03). `unread_count` covers every page. */
export interface NotificationPage extends Paginated<Notification> {
  unread_count: number
}

/** One row of GET /api/cards?assignee=me (BE-SVC-05). */
export interface AssignedCard {
  id: string
  title: string
  column_id: string
  column_name: string
  board_id: string
  board_name: string
  completed_at: string | null
}

/** PATCH /api/cards/<id>/position response (BE-ORD-02). */
export interface CardMoveResult extends Card {
  rebalanced: boolean
  siblings: { id: string; order: number }[]
}

/** BE-ANL-01 analytics payload. */
export interface Analytics {
  week_start: string
  cards_per_column: { column_id: string; name: string; total_cards: number }[]
  completed_this_week: number
  member_activity: {
    user_id: string
    name: string
    cards_created: number
    comments_added: number
    cards_assigned: number
    assigned_cards_completed_this_week: number
  }[]
}
