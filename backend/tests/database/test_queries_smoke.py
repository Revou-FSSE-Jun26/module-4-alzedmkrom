"""Reference queries against the V4 schema (Requirements 6.3, 7.2 to 7.6, 9.8).

The query functions read through db.session, so these tests commit their data
to a scratch database instead of using the rolled-back session fixture.
"""

from datetime import datetime, timedelta, timezone

import pytest
from flask_migrate import upgrade

from app.extensions import db
from app.models import Notification
from app.models import queries
from tests.database.conftest import make_app, migrations_dir
from tests.database.factories import (
    new_board,
    new_card,
    new_column,
    new_comment,
    new_member,
    new_user,
)

UTC = timezone.utc
NOW = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


@pytest.fixture()
def qapp(scratch_url):
    app = make_app(scratch_url)
    with app.app_context():
        upgrade(directory=migrations_dir())
        yield app


def test_week_bounds_are_monday_to_monday_utc():
    start, end = queries.week_bounds_utc(NOW)
    assert start.weekday() == 0
    assert (start.hour, start.minute, start.second) == (0, 0, 0)
    assert end - start == timedelta(days=7)
    assert start <= NOW < end
    # The last second of the previous Sunday belongs to the previous week.
    assert queries.week_bounds_utc(start - timedelta(seconds=1))[0] == start - timedelta(days=7)


def test_board_reports_counts_activity_completions_and_my_tasks(qapp):
    start, end = queries.week_bounds_utc(NOW)
    alice = new_user(db.session, name="Alice")
    bob = new_user(db.session, name="Bob")
    carol = new_user(db.session, name="Carol")  # Guest: never listed
    board = new_board(db.session, creator=alice)
    new_member(db.session, board, alice, role="admin")
    new_member(db.session, board, bob, role="member", added_by=alice)
    todo = new_column(db.session, board, name="To Do", position=1.0)
    done = new_column(db.session, board, name="Done", position=2.0, is_done=True)

    c1 = new_card(db.session, todo, title="c1", position=1.0, creator=alice, assignee=bob)
    c2 = new_card(db.session, todo, title="c2", position=2.0, creator=bob, assignee=alice)
    c3 = new_card(db.session, done, title="c3 deleted", creator=alice)
    c4 = new_card(db.session, done, title="c4 at end", creator=alice)
    c5 = new_card(db.session, done, title="c5 in week", creator=alice)
    c2.completed_at = start
    c3.completed_at = start + timedelta(days=1)
    c3.soft_delete()
    c4.completed_at = end
    c5.completed_at = start + timedelta(days=2)
    db.session.flush()
    new_comment(db.session, c1, content="bob here", creator=bob)
    new_comment(db.session, c1, content="alice here", creator=alice)
    new_comment(db.session, c3, content="on a deleted card", creator=bob)
    db.session.commit()

    counts = {row.name: row.card_count for row in queries.card_counts_per_column(board.id)}
    assert counts == {"To Do": 2, "Done": 2}

    assert queries.completed_this_week(board.id, now=NOW) == 2

    activity = [
        (row.name, row.cards_created, row.comments_added, row.cards_assigned)
        for row in queries.member_activity(board.id)
    ]
    assert activity == [("Alice", 3, 1, 1), ("Bob", 1, 1, 1)]

    my_board_ids = [row[0] for row in queries.my_tasks(alice.id)]
    assert my_board_ids == [board.id]
    assert [row[2].id for row in queries.my_tasks(alice.id)] == [c2.id]

    loaded_board, columns, cards = queries.load_board(board.id)
    assert loaded_board.id == board.id
    assert [c.name for c in columns] == ["To Do", "Done"]
    assert sorted(c.title for c in cards) == ["c1", "c2", "c4 at end", "c5 in week"]


def test_search_is_case_insensitive_and_treats_wildcards_literally(qapp):
    user = new_user(db.session)
    board = new_board(db.session, creator=user)
    column = new_column(db.session, board)
    new_card(db.session, column, title="Alpha launch", creator=user)
    new_card(db.session, column, title="Other", creator=user)
    described = new_card(db.session, column, title="Plain", creator=user)
    described.description = "mentions ALPHA in the body"
    new_card(db.session, column, title="100% done", creator=user)
    new_card(db.session, column, title="snake_case note", creator=user)
    deleted = new_card(db.session, column, title="alpha deleted", creator=user)
    deleted.soft_delete()
    db.session.commit()

    titles = lambda term: sorted(c.title for c in queries.search_cards(term))  # noqa: E731
    assert titles("alpha") == ["Alpha launch", "Plain"]
    assert titles("100%") == ["100% done"]
    assert titles("%") == ["100% done"]
    assert titles("_case") == ["snake_case note"]
    with pytest.raises(ValueError):
        queries.search_cards("")
    with pytest.raises(ValueError):
        queries.search_cards("x" * 201)


def test_notification_page_is_newest_first_and_sliced(qapp):
    user = new_user(db.session)
    base = datetime(2026, 11, 1, tzinfo=UTC)
    for day in range(5):
        db.session.add(Notification(
            user_id=user.id,
            type="comment_added",
            message=f"message {day}",
            created_at=base + timedelta(days=day),
        ))
    db.session.commit()

    page = queries.notifications_page(user.id, limit=2, offset=1)
    assert [n.message for n in page] == ["message 3", "message 2"]
    assert len(queries.notifications_page(user.id, limit=100)) == 5
    with pytest.raises(ValueError):
        queries.notifications_page(user.id, limit=0)


def test_load_board_handles_a_board_without_columns(qapp):
    user = new_user(db.session)
    board = new_board(db.session, creator=user)
    db.session.commit()
    loaded, columns, cards = queries.load_board(board.id)
    assert loaded.id == board.id
    assert columns == []
    assert cards == []

