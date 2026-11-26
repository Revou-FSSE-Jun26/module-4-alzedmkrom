"""Cascade and soft-delete tests against PostgreSQL 18 (DB-TST-01, DB-CAS-01, DB-SOFT-01).

Deletes run as raw SQL, so the database rules do the work, not the ORM.
"""

from sqlalchemy import text

from app.models import Card, Notification
from tests.database.factories import (
    new_board,
    new_card,
    new_column,
    new_comment,
    new_member,
    new_user,
)


def _count(sess, sql, **params):
    return sess.execute(text(sql), params).scalar_one()


def test_board_delete_removes_memberships_columns_cards_and_comments(session):
    alice = new_user(session, name="Alice")
    bob = new_user(session, name="Bob")
    board = new_board(session, creator=alice)
    new_member(session, board, alice, role="admin")
    new_member(session, board, bob, role="member", added_by=alice)
    to_do = new_column(session, board, name="To Do", position=1.0, creator=alice)
    done = new_column(session, board, name="Done", position=2.0, is_done=True)
    live = new_card(session, to_do, creator=alice, assignee=bob)
    soft = new_card(session, done, creator=alice)
    soft.soft_delete()
    session.flush()
    new_comment(session, live, creator=bob)
    new_comment(session, soft, creator=alice)
    notification = Notification(user_id=bob.id, type="card_assigned", message="Assigned", board_id=board.id)
    session.add(notification)
    session.flush()

    session.execute(text("DELETE FROM boards WHERE id = :id"), {"id": board.id})

    assert _count(session, "SELECT count(*) FROM board_members WHERE board_id = :id", id=board.id) == 0
    assert _count(session, "SELECT count(*) FROM columns WHERE board_id = :id", id=board.id) == 0
    # The soft-deleted card goes too: its row is removed by the column cascade.
    assert _count(session, "SELECT count(*) FROM cards WHERE board_id = :id", id=board.id) == 0
    assert _count(
        session,
        "SELECT count(*) FROM comments WHERE card_id IN (:live, :soft)",
        live=live.id,
        soft=soft.id,
    ) == 0
    # Notifications are kept, with their text and their board_id (DB-NTF-01).
    kept = session.execute(
        text("SELECT board_id, message FROM notifications WHERE id = :id"),
        {"id": notification.id},
    ).one()
    assert kept.board_id == board.id
    assert kept.message == "Assigned"
    # Users are not touched by a board delete.
    assert _count(session, "SELECT count(*) FROM users WHERE id IN (:a, :b)", a=alice.id, b=bob.id) == 2


def test_user_delete_nulls_owner_references_and_keeps_the_rows(session):
    owner = new_user(session, name="Owner")
    other = new_user(session, name="Other")
    board = new_board(session, creator=owner)
    new_member(session, board, owner, role="admin")
    new_member(session, board, other, role="member", added_by=owner)
    column = new_column(session, board, creator=owner)
    card = new_card(session, column, creator=owner, assignee=owner)
    comment = new_comment(session, card, creator=owner)

    # Must not raise (DB-OWN-01, DB-CAS-01).
    session.execute(text("DELETE FROM users WHERE id = :id"), {"id": owner.id})

    row = session.execute(
        text("SELECT created_by FROM boards WHERE id = :id"), {"id": board.id}
    ).one()
    assert row.created_by is None
    assert session.execute(
        text("SELECT created_by FROM columns WHERE id = :id"), {"id": column.id}
    ).scalar_one() is None
    card_row = session.execute(
        text("SELECT created_by, assignee_id FROM cards WHERE id = :id"), {"id": card.id}
    ).one()
    assert card_row.created_by is None
    assert card_row.assignee_id is None
    assert session.execute(
        text("SELECT created_by FROM comments WHERE id = :id"), {"id": comment.id}
    ).scalar_one() is None
    # The deleted user's own membership is removed; the other member's added_by is nulled.
    assert _count(session, "SELECT count(*) FROM board_members WHERE board_id = :id", id=board.id) == 1
    assert session.execute(
        text("SELECT added_by FROM board_members WHERE user_id = :id"), {"id": other.id}
    ).scalar_one() is None
    # Work the user created stays on the board.
    assert _count(session, "SELECT count(*) FROM cards WHERE id = :id", id=card.id) == 1


def test_column_delete_removes_its_cards_and_their_comments(session):
    user = new_user(session)
    board = new_board(session, creator=user)
    doomed = new_column(session, board, name="Doomed")
    kept = new_column(session, board, name="Kept", position=2.0)
    card = new_card(session, doomed, creator=user)
    new_comment(session, card, creator=user)
    survivor = new_card(session, kept, creator=user)

    session.execute(text("DELETE FROM columns WHERE id = :id"), {"id": doomed.id})

    assert _count(session, "SELECT count(*) FROM cards WHERE id = :id", id=card.id) == 0
    assert _count(session, "SELECT count(*) FROM comments WHERE card_id = :id", id=card.id) == 0
    assert _count(session, "SELECT count(*) FROM cards WHERE id = :id", id=survivor.id) == 1


def test_soft_deleted_card_keeps_its_row_and_is_excluded_from_active(session):
    user = new_user(session)
    board = new_board(session, creator=user)
    column = new_column(session, board)
    live = new_card(session, column, title="Live", creator=user)
    soft = new_card(session, column, title="Soft", creator=user)
    soft.soft_delete()
    session.flush()

    row = session.execute(
        text("SELECT deleted_at FROM cards WHERE id = :id"), {"id": soft.id}
    ).one()
    assert row.deleted_at is not None

    # Card.active() is the single live-card filter (DB-SOFT-02).
    active = {c.id for c in session.scalars(Card.active().statement)}
    assert live.id in active
    assert soft.id not in active


def test_hard_deleting_a_card_row_removes_its_comments(session):
    user = new_user(session)
    board = new_board(session, creator=user)
    column = new_column(session, board)
    card = new_card(session, column, creator=user)
    new_comment(session, card, creator=user)

    session.execute(text("DELETE FROM cards WHERE id = :id"), {"id": card.id})

    assert _count(session, "SELECT count(*) FROM comments WHERE card_id = :id", id=card.id) == 0
