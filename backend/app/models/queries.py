"""Reference queries for the V4 schema (Requirements 6.3, 7.2 to 7.6, 9.8).

A card is "live" when ``cards.deleted_at IS NULL``. Columns and boards are
hard-deleted, so no query filters on a parent's deletion state.
"""

from datetime import datetime, time, timedelta, timezone

from sqlalchemy import and_, func, or_, select

from app.extensions import db
from app.models import Board, BoardColumn, BoardMember, Card, Comment, Notification, User

UTC = timezone.utc


def week_bounds_utc(now: datetime) -> tuple[datetime, datetime]:
    """Monday 00:00 UTC (inclusive) and the next Monday 00:00 UTC (exclusive)."""
    now = now.astimezone(UTC)
    monday = now.date() - timedelta(days=now.weekday())
    start = datetime.combine(monday, time.min, tzinfo=UTC)
    return start, start + timedelta(days=7)


def card_counts_per_column(board_id):
    """Req 7.2. Empty columns return 0. The deleted_at test sits in the ON clause."""
    return db.session.execute(
        select(BoardColumn.id, BoardColumn.name, func.count(Card.id).label("card_count"))
        .outerjoin(
            Card,
            and_(Card.column_id == BoardColumn.id, Card.deleted_at.is_(None)),
        )
        .where(BoardColumn.board_id == board_id)
        .group_by(BoardColumn.id, BoardColumn.name, BoardColumn.order)
        .order_by(BoardColumn.order)
    ).all()


def completed_this_week(board_id, now=None):
    """Req 7.3. Filters on cards.board_id, served by ix_cards_board_id_completed_at."""
    start, end = week_bounds_utc(now or datetime.now(UTC))
    return db.session.scalar(
        select(func.count(Card.id)).where(
            Card.board_id == board_id,
            Card.deleted_at.is_(None),
            Card.completed_at >= start,
            Card.completed_at < end,
        )
    )


def member_activity(board_id):
    """Req 7.4 (OD-6). One row per current member with three counts; zeros included.

    cards_created: live cards where created_by is the member.
    comments_added: comments on live cards where created_by is the member.
    cards_assigned: live cards where assignee_id is the member.
    Members whose membership was removed are not listed.
    """
    created = (
        select(Card.created_by.label("user_id"), func.count().label("n"))
        .where(
            Card.board_id == board_id,
            Card.deleted_at.is_(None),
            Card.created_by.is_not(None),
        )
        .group_by(Card.created_by)
        .subquery()
    )
    commented = (
        select(Comment.created_by.label("user_id"), func.count().label("n"))
        .join(Card, Card.id == Comment.card_id)
        .where(
            Card.board_id == board_id,
            Card.deleted_at.is_(None),
            Comment.created_by.is_not(None),
        )
        .group_by(Comment.created_by)
        .subquery()
    )
    assigned = (
        select(Card.assignee_id.label("user_id"), func.count().label("n"))
        .where(
            Card.board_id == board_id,
            Card.deleted_at.is_(None),
            Card.assignee_id.is_not(None),
        )
        .group_by(Card.assignee_id)
        .subquery()
    )
    return db.session.execute(
        select(
            User.id,
            User.name,
            func.coalesce(created.c.n, 0).label("cards_created"),
            func.coalesce(commented.c.n, 0).label("comments_added"),
            func.coalesce(assigned.c.n, 0).label("cards_assigned"),
        )
        .join(
            BoardMember,
            and_(BoardMember.user_id == User.id, BoardMember.board_id == board_id),
        )
        .outerjoin(created, created.c.user_id == User.id)
        .outerjoin(commented, commented.c.user_id == User.id)
        .outerjoin(assigned, assigned.c.user_id == User.id)
        .order_by(User.name)
    ).all()


def my_tasks(user_id):
    """Req 7.5. Live cards assigned to the user, joined through cards.board_id."""
    return db.session.execute(
        select(Board.id, Board.name, Card)
        .join(Card, Card.board_id == Board.id)
        .join(BoardColumn, BoardColumn.id == Card.column_id)
        .where(Card.assignee_id == user_id, Card.deleted_at.is_(None))
        .order_by(Board.name, BoardColumn.order, Card.order)
    ).all()


def search_cards(term: str, user_id=None):
    """Req 7.6. Case-insensitive substring match on title or description.

    The term is 1 to 200 characters. The optional user_id limits results to
    boards that user belongs to.
    """
    if not 1 <= len(term) <= 200:
        raise ValueError("search term must be 1 to 200 characters")
    stmt = select(Card).where(
        Card.deleted_at.is_(None),
        or_(
            Card.title.icontains(term, autoescape=True),
            Card.description.icontains(term, autoescape=True),
        ),
    )
    if user_id is not None:
        stmt = stmt.join(
            BoardMember,
            and_(BoardMember.board_id == Card.board_id, BoardMember.user_id == user_id),
        )
    return db.session.scalars(stmt).all()


def notifications_page(user_id, limit=20, offset=0):
    """Req 6.3. Newest first; served by ix_notifications_user_id_created_at."""
    if not 1 <= limit <= 100 or not 0 <= offset <= 1_000_000:
        raise ValueError("limit must be 1 to 100 and offset 0 to 1000000")
    return db.session.scalars(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()


def load_board(board_id):
    """Req 9.8. Three indexed queries: the board, its columns, its live cards."""
    board = db.session.get(Board, board_id)
    columns = db.session.scalars(
        select(BoardColumn)
        .where(BoardColumn.board_id == board_id)
        .order_by(BoardColumn.order)
    ).all()
    cards = (
        Card.active()
        .filter(Card.column_id.in_([c.id for c in columns]))
        .order_by(Card.column_id, Card.order)
        .all()
    )
    return board, columns, cards
