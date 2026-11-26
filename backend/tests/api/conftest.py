"""Fixtures for API tests (BE-TST-01). Real PostgreSQL 18 only, never SQLite.

The schema comes from `tests.database.conftest.flask_app`, which runs
`flask db upgrade` once per session. Tests reuse that database and empty the
tables before each test.
"""
import itertools
import os

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import text
from werkzeug.security import generate_password_hash

# The real package must be imported before tests.database.conftest. That module
# registers a bare `app` package when `app` is not yet imported.
import app as _app_package  # noqa: F401
from app.extensions import db
from app.models import Board, BoardColumn, BoardMember, Card, Comment, Notification, User
from tests.database.conftest import database_url, flask_app  # noqa: F401

TABLES = ("users", "boards", "board_members", "columns", "cards", "comments", "notifications")
TEST_PASSWORD = "Password123!"
_PASSWORD_HASH = generate_password_hash(TEST_PASSWORD)
_seq = itertools.count(1)


@pytest.fixture(scope="session")
def api_app(database_url, flask_app):  # noqa: F811
    from app import create_app

    os.environ["DATABASE_URL"] = database_url
    return create_app(verify_db=False)


@pytest.fixture(autouse=True)
def app_ctx(api_app):
    with api_app.app_context():
        db.session.remove()
        db.session.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
        db.session.commit()
        yield api_app
        db.session.remove()


def _client(api_app, user=None):
    client = api_app.test_client()
    if user is not None:
        token = create_access_token(identity=str(user.id))
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


def _save(obj):
    db.session.add(obj)
    db.session.commit()
    return obj


@pytest.fixture()
def api_client(api_app):
    """Factory: `api_client(user)` returns a client that sends that user's token."""
    return lambda user=None: _client(api_app, user)


@pytest.fixture()
def make_user(app_ctx):
    def factory(name=None, email=None):
        n = next(_seq)
        return _save(
            User(
                name=name or f"User {n}",
                email=(email or f"user{n}@example.com").lower(),
                password_hash=_PASSWORD_HASH,
            )
        )

    return factory


@pytest.fixture()
def make_board(app_ctx):
    def factory(owner, members=(), *, public=True, name=None):
        board = Board(name=name or f"Board {next(_seq)}", is_public=public, created_by=owner.id)
        db.session.add(board)
        db.session.flush()
        db.session.add(BoardMember(board_id=board.id, user_id=owner.id, role="admin", added_by=owner.id))
        for member in members:
            db.session.add(
                BoardMember(board_id=board.id, user_id=member.id, role="member", added_by=owner.id)
            )
        db.session.commit()
        return board

    return factory


@pytest.fixture()
def make_column(app_ctx):
    def factory(board, *, name=None, order=None, is_done=False, creator=None):
        n = next(_seq)
        return _save(
            BoardColumn(
                board_id=board.id,
                name=name or f"Column {n}",
                order=float(n * 1024) if order is None else order,
                is_done=is_done,
                created_by=None if creator is None else creator.id,
            )
        )

    return factory


@pytest.fixture()
def make_card(app_ctx):
    def factory(column, creator, *, title=None, order=None, assignee=None, completed_at=None):
        n = next(_seq)
        return _save(
            Card(
                board_id=column.board_id,
                column_id=column.id,
                title=title or f"Card {n}",
                order=float(n * 1024) if order is None else order,
                assignee_id=None if assignee is None else assignee.id,
                created_by=creator.id,
                completed_at=completed_at,
            )
        )

    return factory


@pytest.fixture()
def make_comment(app_ctx):
    def factory(card, author, content=None):
        return _save(
            Comment(
                card_id=card.id,
                content=content or f"Comment {next(_seq)}",
                created_by=author.id,
            )
        )

    return factory


@pytest.fixture()
def make_notification(app_ctx):
    def factory(user, board, *, type="card_assigned", message=None):
        return _save(
            Notification(
                user_id=user.id,
                type=type,
                message=message or f"Notification {next(_seq)}",
                board_id=board.id,
            )
        )

    return factory


@pytest.fixture()
def people(make_user):
    """Named users used by the role fixtures below."""
    return {
        "admin": make_user("Ada Admin", "admin@example.com"),
        "member": make_user("Mel Member", "member@example.com"),
        "other_member": make_user("Oli Other", "other@example.com"),
        "guest": make_user("Gus Guest", "guest@example.com"),
        "outside_admin": make_user("Olga Outside", "outside@example.com"),
    }


@pytest.fixture()
def board(make_board, people):
    """Public board: admin is Admin, member and other_member are Members, guest has no row."""
    return make_board(people["admin"], [people["member"], people["other_member"]], name="Team board")


@pytest.fixture()
def private_board(make_board, people):
    return make_board(
        people["admin"], [people["member"]], public=False, name="Private board"
    )


@pytest.fixture()
def outside_board(make_board, people):
    return make_board(people["outside_admin"], name="Other board")


@pytest.fixture()
def column(make_column, board):
    return make_column(board, name="To do", order=1024.0)


@pytest.fixture()
def anonymous_client(api_client):
    return api_client(None)


@pytest.fixture()
def guest_client(api_client, people):
    return api_client(people["guest"])


@pytest.fixture()
def member_client(api_client, people):
    return api_client(people["member"])


@pytest.fixture()
def other_member_client(api_client, people):
    return api_client(people["other_member"])


@pytest.fixture()
def admin_client(api_client, people):
    return api_client(people["admin"])


@pytest.fixture()
def outside_admin_client(api_client, people):
    return api_client(people["outside_admin"])


def error_code(response):
    body = response.get_json()
    assert set(body) == {"error"}, body
    assert set(body["error"]) == {"code", "message", "details"}, body
    return body["error"]["code"]
