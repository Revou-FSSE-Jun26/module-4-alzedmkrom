export type Role = 'admin' | 'member'
export type NotificationType = 'card_assigned' | 'card_moved' | 'comment_added' | 'member_added'

export interface User { id: string; name: string; email: string }                    // login "user", /users/me
export interface RegisteredUser extends User { created_at: string }
export interface LoginResponse { access_token: string; token_type: string; expires_in: number; user: User }

export interface Board { id: string; name: string; owner_id: string; role: Role; created_at: string; updated_at: string }
export interface Column { id: string; board_id: string; title: string; order: number; created_at: string; updated_at: string }
export interface Card {
  id: string; title: string; description: string | null; assignee_id: string | null; created_by: string
  order: number; completed_at: string | null; created_at: string; updated_at: string
}
export interface ColumnWithCards extends Column { cards: Card[] }
export interface BoardDetail extends Board { columns: ColumnWithCards[] }

export interface Member { user_id: string; name: string; email: string; role: Role; created_at: string }
export interface Comment { id: string; card_id: string; content: string; author: { id: string; name: string }; created_at: string; updated_at: string }
export interface Notification {
  id: string; type: NotificationType; message: string; board_id: string; card_id: string | null; is_read: boolean; created_at: string
}
export interface NotificationPage { items: Notification[]; page: number; per_page: number; total: number }
export interface MyTasksGroup { board_id: string; board_name: string; cards: Card[] }
export interface Analytics {
  cards_per_column: { column_id: string; title: string; card_count: number }[]
  completed_this_week: number
  member_activity: { user_id: string; name: string; actions: number }[]
}
export interface CardMoveResult extends Card { column_id: string; rebalanced: boolean; siblings?: { id: string; order: number }[] }
export interface ColumnReorderResult { columns: Column[]; rebalanced: boolean }
export interface DeletedId { id: string }
export interface MemberRemoved { user_id: string }
