"""Constraint tests against PostgreSQL 18 (DB-TST-01).

Each test inserts directly through SQLAlchemy and expects the database to reject
or accept the row. The application layer is not involved. Each test runs in a
transaction that is rolled back.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError

from app.models import Card, Notification, User
from tests.database.factories import (
    new_board,
    new_card,
    new_column,
    new_comment,
    new_member,
    new_user,
)


@pytest.fixture()
def board(session):
    creator = new_user(session)
    return new_board(session, creator=creator)


@pytest.fixture()
def column(session, board):
    return new_column(session, board)


# ---------------------------------------------------------------------------
# Users and boards
# ---------------------------------------------------------------------------


def test_email_is_unique_ignoring_case(session, failing):
    new_user(session, email="Dup@Example.com")
    with pytest.raises(IntegrityError, match="uq_users_email_lower"):
        with failing(session):
            new_user(session, email="dup@example.COM")


def _user_with_empty_hash(sess, board):
    sess.add(User(name="n", email=f"{uuid.uuid4().hex}@example.com", password_hash=""))
    sess.flush()


def _user_with_short_email(sess, board):
    new_user(sess, email="ab")


def _user_with_empty_name(sess, board):
    new_user(sess, name="")


def _board_with_empty_name(sess, board):
    new_board(sess, name="")


def _column_with_empty_name(sess, board):
    new_column(sess, board, name="")


def _card_with_empty_title(sess, board):
    new_card(sess, new_column(sess, board), title="")


MINIMUM_LENGTH_CASES = [
    pytest.param(_user_with_empty_name, "ck_users_name_length", id="users.name"),
    pytest.param(_user_with_short_email, "ck_users_email_length", id="users.email"),
    pytest.param(_user_with_empty_hash, "ck_users_password_hash_length", id="users.password_hash"),
    pytest.param(_board_with_empty_name, "ck_boards_name_length", id="boards.name"),
    pytest.param(_column_with_empty_name, "ck_columns_name_length", id="columns.name"),
    pytest.param(_card_with_empty_title, "ck_cards_title_length", id="cards.title"),
]


@pytest.mark.parametrize("build, constraint", MINIMUM_LENGTH_CASES)
def test_minimum_length_checks_reject_empty_values(session, failing, board, build, constraint):
    with pytest.raises(IntegrityError, match=constraint):
        with failing(session):
            build(session, board)


def _name_of_101_chars(sess, board):
    new_board(sess, name="b" * 101)


def _title_of_201_chars(sess, board):
    new_card(sess, new_column(sess, board), title="t" * 201)


def _column_name_of_101_chars(sess, board):
    new_column(sess, board, name="c" * 101)


def _user_name_of_101_chars(sess, board):
    new_user(sess, name="u" * 101)


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(_name_of_101_chars, id="boards.name"),
        pytest.param(_title_of_201_chars, id="cards.title"),
        pytest.param(_column_name_of_101_chars, id="columns.name"),
        pytest.param(_user_name_of_101_chars, id="users.name"),
    ],
)
def test_varchar_limits_are_enforced_by_the_type(session, failing, board, build):
    with pytest.raises(DataError):
        with failing(session):
            build(session, board)


# ---------------------------------------------------------------------------
# Columns and cards
# ---------------------------------------------------------------------------


def test_second_done_column_on_one_board_is_rejected(session, failing, board):
    new_column(session, board, name="Done A", is_done=True)
    with pytest.raises(IntegrityError, match="uq_columns_board_id_done"):
        with failing(session):
            new_column(session, board, name="Done B", is_done=True)


def test_done_columns_on_different_boards_are_allowed(session, board):
    new_column(session, board, name="Done", is_done=True)
    other = new_board(session, creator=None)
    new_column(session, other, name="Done", is_done=True)


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_column_position_must_be_positive(session, failing, board, value):
    with pytest.raises(IntegrityError, match="ck_columns_position"):
        with failing(session):
            new_column(session, board, position=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf")], ids=["nan", "infinity"])
def test_column_position_rejects_nan_and_infinity(session, failing, board, value):
    with pytest.raises(IntegrityError, match="ck_columns_position"):
        with failing(session):
            new_column(session, board, position=value)


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_card_position_must_be_positive(session, failing, column, value):
    with pytest.raises(IntegrityError, match="ck_cards_position"):
        with failing(session):
            new_card(session, column, position=value)


@pytest.mark.parametrize("value", [float("nan"), float("inf")], ids=["nan", "infinity"])
def test_card_position_rejects_nan_and_infinity(session, failing, column, value):
    with pytest.raises(IntegrityError, match="ck_cards_position"):
        with failing(session):
            new_card(session, column, position=value)


def test_card_cannot_move_to_a_column_of_another_board(session, failing, board, column):
    other_board = new_board(session, creator=None)
    other_column = new_column(session, other_board)
    card = new_card(session, column)
    with pytest.raises(IntegrityError, match="fk_cards_column_id_columns"):
        with failing(session):
            session.execute(
                text("UPDATE cards SET column_id = :col WHERE id = :id"),
                {"col": other_column.id, "id": card.id},
            )


def test_card_cannot_be_created_with_a_mismatched_board(session, failing, board, column):
    other_board = new_board(session, creator=None)
    with pytest.raises(IntegrityError, match="fk_cards_column_id_columns"):
        with failing(session):
            session.add(
                Card(board_id=other_board.id, column_id=column.id, title="x", order=1.0)
            )
            session.flush()


@pytest.mark.parametrize(
    "length, accepted",
    [(5000, True), (5001, False)],
    ids=["5000", "5001"],
)
def test_card_description_length(session, failing, column, length, accepted):
    def set_description():
        card = new_card(session, column)
        card.description = "d" * length
        session.flush()

    if accepted:
        set_description()
        return
    with pytest.raises(IntegrityError, match="ck_cards_description_length"):
        with failing(session):
            set_description()


# ---------------------------------------------------------------------------
# Memberships and comments
# ---------------------------------------------------------------------------


def test_invalid_membership_role_is_rejected(session, failing, board):
    user = new_user(session)
    with pytest.raises(IntegrityError, match="ck_board_members_role"):
        with failing(session):
            new_member(session, board, user, role="owner")


def test_duplicate_membership_is_rejected(session, failing, board):
    user = new_user(session)
    new_member(session, board, user, role="member")
    with pytest.raises(IntegrityError, match="pk_board_members"):
        with failing(session):
            new_member(session, board, user, role="admin")


@pytest.mark.parametrize(
    "length, accepted",
    [(0, False), (1, True), (2000, True), (2001, False)],
    ids=["0", "1", "2000", "2001"],
)
def test_comment_content_length(session, failing, column, length, accepted):
    card = new_card(session, column)
    content = "x" * length
    if accepted:
        new_comment(session, card, content=content)
        return
    with pytest.raises(IntegrityError, match="ck_comments_content_length"):
        with failing(session):
            new_comment(session, card, content=content)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def test_notification_type_must_be_in_the_allowed_list(session, failing):
    user = new_user(session)
    with pytest.raises(IntegrityError, match="ck_notifications_type"):
        with failing(session):
            session.add(Notification(user_id=user.id, type="bogus", message="m"))
            session.flush()


def test_notification_type_accepts_the_allowed_values(session):
    user = new_user(session)
    kinds = ("card_assigned", "card_moved", "comment_added", "member_added")
    for kind in kinds:
        session.add(Notification(user_id=user.id, type=kind, message="m"))
    session.flush()
    assert session.query(Notification).filter_by(user_id=user.id).count() == len(kinds)
