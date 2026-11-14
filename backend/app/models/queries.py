"""Reference queries (Requirements 6.3, 6.6, 7.2 to 7.6, 9.8).

A card is "live" when ``cards.deleted_at IS NULL`` and neither its column nor
its board is soft-deleted. Soft-deleting a parent hides its contents.
"""

from datetime import datetime, time, timedelta, timezone

from sqlalchemy import and_, func, or_, select

from app.extensions import db
from app.models import (
    ActivityLog,
    Board,
    BoardColumn,
    BoardMember,
    Card,
    Notification,
    User,
)

UTC = timezone.utc

SEARCH_TERM_MIN = 1
SEARCH_TERM_MAX = 200
NOTIFICATION_LIMIT_MIN = 1
NOTIFICATION_LIMIT_MAX = 100
NOTIFICATION_OFFSET_MIN = 0
NOTIFICATION_OFFSET_MAX = 1_000_000


def week_bounds_utc(now: datetime) -> tuple[datetime, datetime]:
    """Monday 00:00 UTC (inclusive) and next Monday 00:00 UTC (exclusive)."""
    now = now.astimezone(UTC)
    monday = now.date() - timedelta(days=now.weekday())
    start = datetime.combine(monday, time.min, tzinfo=UTC)
    return start, start + timedelta(days=7)


def card_counts_per_column(board_id):
    """Live cards per live column of a board. Empty columns return 0 (Req 7.2)."""
    return db.session.execute(
        select(
            BoardColumn.id,
            BoardColumn.title,
            func.count(Card.id).label("card_count"),
        )
        .join(Board, Board.id == BoardColumn.board_id)
        .outerjoin(
            Card, and_(Card.column_id == BoardColumn.id, Card.deleted_at.is_(None))
        )
        .where(
            BoardColumn.board_id == board_id,
            BoardColumn.deleted_at.is_(None),
            Board.deleted_at.is_(None),
        )
        .group_by(BoardColumn.id, BoardColumn.title, BoardColumn.order)
        .order_by(BoardColumn.order)
    ).all()


def completed_this_week(board_id, now=None):
    """Live cards completed between this Monday 00:00 UTC and the next (Req 7.3)."""
    start, end = week_bounds_utc(now or datetime.now(UTC))
    return db.session.scalar(
        select(func.count(Card.id))
        .join(BoardColumn, Card.column_id == BoardColumn.id)
        .join(Board, BoardColumn.board_id == Board.id)
        .where(
            BoardColumn.board_id == board_id,
            Card.deleted_at.is_(None),
            BoardColumn.deleted_at.is_(None),
            Board.deleted_at.is_(None),
            Card.completed_at >= start,
            Card.completed_at < end,
        )
    )


def member_activity(board_id):
    """Activity count per user. Members with no logs appear with 0; former
    members appear only if they have logs on the board (Req 7.4)."""
    member_ids = select(BoardMember.user_id).where(BoardMember.board_id == board_id)
    actor_ids = select(ActivityLog.user_id).where(ActivityLog.board_id == board_id)
    return db.session.execute(
        select(User.id, User.name, func.count(ActivityLog.id).label("actions"))
        .outerjoin(
            ActivityLog,
            and_(ActivityLog.user_id == User.id, ActivityLog.board_id == board_id),
        )
        .where(or_(User.id.in_(member_ids), User.id.in_(actor_ids)))
        .group_by(User.id, User.name)
    ).all()


def my_tasks(user_id):
    """Live cards assigned to a user, ordered by board name (Req 7.5).

    Rows are ``(board_id, board_name, Card)``; callers may group them with
    ``itertools.groupby`` on the board name.
    """
    return db.session.execute(
        select(Board.id, Board.name, Card)
        .join(BoardColumn, BoardColumn.board_id == Board.id)
        .join(Card, Card.column_id == BoardColumn.id)
        .where(
            Card.assignee_id == user_id,
            Card.deleted_at.is_(None),
            BoardColumn.deleted_at.is_(None),
            Board.deleted_at.is_(None),
        )
        .order_by(Board.name, BoardColumn.order, Card.order)
    ).all()


def search_cards(term: str, user_id=None):
    """Case-insensitive substring search on title or description (Req 7.6)."""
    if not isinstance(term, str) or not (
        SEARCH_TERM_MIN <= len(term) <= SEARCH_TERM_MAX
    ):
        raise ValueError(
            f"search term must be {SEARCH_TERM_MIN} to {SEARCH_TERM_MAX} characters"
        )
    stmt = (
        select(Card)
        .join(BoardColumn, Card.column_id == BoardColumn.id)
        .join(Board, BoardColumn.board_id == Board.id)
        .where(
            Card.deleted_at.is_(None),
            BoardColumn.deleted_at.is_(None),
            Board.deleted_at.is_(None),
            or_(
                Card.title.icontains(term, autoescape=True),
                Card.description.icontains(term, autoescape=True),
            ),
        )
    )
    if user_id is not None:
        stmt = stmt.join(
            BoardMember,
            and_(BoardMember.board_id == Board.id, BoardMember.user_id == user_id),
        )
    return db.session.scalars(stmt).all()


def notifications_page(user_id, limit=20, offset=0):
    """One page of a user's notifications, newest first (Req 6.3, 6.6)."""
    if not (NOTIFICATION_LIMIT_MIN <= limit <= NOTIFICATION_LIMIT_MAX):
        raise ValueError(
            f"limit must be {NOTIFICATION_LIMIT_MIN} to {NOTIFICATION_LIMIT_MAX}"
        )
    if not (NOTIFICATION_OFFSET_MIN <= offset <= NOTIFICATION_OFFSET_MAX):
        raise ValueError(
            f"offset must be {NOTIFICATION_OFFSET_MIN} to {NOTIFICATION_OFFSET_MAX}"
        )
    return db.session.scalars(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()


def load_board(board_id):
    """Board, its live columns and their live cards in three queries (Req 9.8)."""
    board = db.session.get(Board, board_id)
    columns = db.session.scalars(
        select(BoardColumn)
        .where(BoardColumn.board_id == board_id, BoardColumn.deleted_at.is_(None))
        .order_by(BoardColumn.order)
    ).all()
    cards = db.session.scalars(
        select(Card)
        .where(
            Card.column_id.in_([c.id for c in columns]),
            Card.deleted_at.is_(None),
        )
        .order_by(Card.column_id, Card.order)
    ).all()
    return board, columns, cards
