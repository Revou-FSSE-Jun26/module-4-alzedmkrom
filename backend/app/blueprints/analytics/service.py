"""Board analytics for Admins (BE-ANL-01, BE-STR-03). All figures come from SQL aggregates."""
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import and_, func, select

from app.extensions import db
from app.models import BoardColumn, BoardMember, Card, Comment, User
from app.permissions import authorize, load_board


def week_bounds(now):
    """Monday 00:00 UTC (inclusive) and the following Monday 00:00 UTC (exclusive)."""
    now = now.astimezone(timezone.utc)
    monday = now.date() - timedelta(days=now.weekday())
    start = datetime.combine(monday, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=7)


def board_analytics(user, board_id, now=None):
    board = load_board(board_id)
    authorize(user, "board:analytics", board)
    start, end = week_bounds(now or datetime.now(timezone.utc))
    live = Card.active().subquery()

    columns = db.session.execute(
        select(BoardColumn.id, BoardColumn.name, func.count(live.c.id))
        .outerjoin(live, live.c.column_id == BoardColumn.id)
        .where(BoardColumn.board_id == board.id)
        .group_by(BoardColumn.id, BoardColumn.name, BoardColumn.order)
        .order_by(BoardColumn.order, BoardColumn.id)
    ).all()

    completed = db.session.scalar(
        select(func.count(live.c.id)).where(
            live.c.board_id == board.id,
            live.c.completed_at >= start,
            live.c.completed_at < end,
        )
    )

    created = (
        select(live.c.created_by.label("user_id"), func.count().label("n"))
        .where(live.c.board_id == board.id, live.c.created_by.isnot(None))
        .group_by(live.c.created_by)
        .subquery()
    )
    commented = (
        select(Comment.created_by.label("user_id"), func.count().label("n"))
        .join(live, live.c.id == Comment.card_id)
        .where(live.c.board_id == board.id, Comment.created_by.isnot(None))
        .group_by(Comment.created_by)
        .subquery()
    )
    assigned = (
        select(live.c.assignee_id.label("user_id"), func.count().label("n"))
        .where(live.c.board_id == board.id, live.c.assignee_id.isnot(None))
        .group_by(live.c.assignee_id)
        .subquery()
    )
    assigned_done = (
        select(live.c.assignee_id.label("user_id"), func.count().label("n"))
        .where(
            live.c.board_id == board.id,
            live.c.assignee_id.isnot(None),
            live.c.completed_at >= start,
            live.c.completed_at < end,
        )
        .group_by(live.c.assignee_id)
        .subquery()
    )
    members = db.session.execute(
        select(
            User.id,
            User.name,
            func.coalesce(created.c.n, 0),
            func.coalesce(commented.c.n, 0),
            func.coalesce(assigned.c.n, 0),
            func.coalesce(assigned_done.c.n, 0),
        )
        .join(BoardMember, and_(BoardMember.user_id == User.id, BoardMember.board_id == board.id))
        .outerjoin(created, created.c.user_id == User.id)
        .outerjoin(commented, commented.c.user_id == User.id)
        .outerjoin(assigned, assigned.c.user_id == User.id)
        .outerjoin(assigned_done, assigned_done.c.user_id == User.id)
        .order_by(User.name, User.id)
    ).all()

    return {
        "week_start": start,
        "cards_per_column": [
            {"column_id": cid, "name": name, "total_cards": total}
            for cid, name, total in columns
        ],
        "completed_this_week": completed,
        "member_activity": [
            {
                "user_id": uid,
                "name": name,
                "cards_created": c,
                "comments_added": m,
                "cards_assigned": a,
                "assigned_cards_completed_this_week": d,
            }
            for uid, name, c, m, a, d in members
        ],
    }
