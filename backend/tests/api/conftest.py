"""Fixtures for API tests (real PostgreSQL 18, isolation by TRUNCATE, design D15).

`database_url`, `app` and `engine` come from `tests.database.conftest`, so the
throwaway cluster, the version assertion and `flask db upgrade` are reused.
The Hypothesis profile of that module is loaded by the import.
"""
import itertools
import uuid
from contextlib import contextmanager

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import event, text
from werkzeug.security import generate_password_hash

from tests.database.conftest import app, database_url, engine  # noqa: F401

TABLES = (
    "users",
    "boards",
    "board_members",
    "columns",
    "cards",
    "comments",
    "notifications",
    "activity_logs",
)

TEST_PASSWORD = "Password123!"
# Hashed once: hashing per user would make the suite slow.
TEST_PASSWORD_HASH = generate_password_hash(TEST_PASSWORD)

_counter = itertools.count(1)


@pytest.fixture()
def app_ctx(app):
    """Application context shared by the factories and `snapshot()`."""
    with app.app_context():
        yield app


@pytest.fixture(autouse=True)
def clean_db(app_ctx, engine):
    """Empty all eight tables before each test (D15)."""
    from app.extensions import db

    def truncate():
        db.session.remove()
        db.session.execute(
            text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")
        )
        db.session.commit()

    truncate()
    yield
    db.session.remove()


@pytest.fixture()
def client(app_ctx):
    return app_ctx.test_client()


def _add(obj):
    from app.extensions import db

    db.session.add(obj)
    db.session.commit()
    return obj


@pytest.fixture()
def make_user(app_ctx):
    def factory(name=None, email=None, password_hash=TEST_PASSWORD_HASH, **kw):
        from app.models.user import User

        n = next(_counter)
        return _add(
            User(
                name=name or f"User {n}",
                email=email or f"user{n}-{uuid.uuid4().hex[:8]}@example.com",
                password_hash=password_hash,
                **kw,
            )
        )

    return factory


@pytest.fixture()
def make_board(app_ctx):
    def factory(owner, members=(), name=None, **kw):
        """Create a board owned by `owner` (admin). `members` get role member."""
        from app.extensions import db
        from app.models.board import Board, BoardMember

        board = Board(name=name or f"Board {next(_counter)}", owner_id=owner.id, **kw)
        db.session.add(board)
        db.session.flush()
        db.session.add(BoardMember(board_id=board.id, user_id=owner.id, role="admin"))
        for m in members:
            if m.id != owner.id:
                db.session.add(BoardMember(board_id=board.id, user_id=m.id, role="member"))
        db.session.commit()
        return board

    return factory


@pytest.fixture()
def make_column(app_ctx):
    def factory(board, title=None, order=None, **kw):
        from app.models.column import BoardColumn

        n = next(_counter)
        return _add(
            BoardColumn(
                board_id=board.id,
                title=title or f"Column {n}",
                order=float(n) if order is None else order,
                **kw,
            )
        )

    return factory


@pytest.fixture()
def make_card(app_ctx):
    def factory(column, creator, title=None, order=None, assignee=None, description=None, **kw):
        from app.models.card import Card

        n = next(_counter)
        return _add(
            Card(
                column_id=column.id,
                created_by=creator.id,
                assignee_id=None if assignee is None else assignee.id,
                title=title or f"Card {n}",
                description=description,
                order=float(n) if order is None else order,
                **kw,
            )
        )

    return factory


@pytest.fixture()
def make_comment(app_ctx):
    def factory(card, author, body=None, **kw):
        from app.models.comment import Comment

        return _add(
            Comment(
                card_id=card.id,
                user_id=author.id,
                body=body or f"Comment {next(_counter)}",
                **kw,
            )
        )

    return factory


@pytest.fixture()
def make_notification(app_ctx):
    def factory(user, board, card=None, type="card_assigned", message=None, **kw):
        from app.models.notification import Notification

        return _add(
            Notification(
                user_id=user.id,
                board_id=board.id,
                card_id=None if card is None else card.id,
                type=type,
                message=message or f"Notification {next(_counter)}",
                **kw,
            )
        )

    return factory


@pytest.fixture()
def auth_headers(app_ctx):
    def factory(user):
        token = create_access_token(identity=str(user.id))
        return {"Authorization": f"Bearer {token}"}

    return factory


@pytest.fixture()
def snapshot(app_ctx):
    """Callable returning row counts and column values of all eight tables."""
    from app.extensions import db

    def take():
        db.session.rollback()  # end any open transaction so the read is current
        result = {}
        for name in TABLES:
            table = db.metadata.tables[name]
            cols = sorted(c.name for c in table.columns)
            rows = db.session.execute(
                text(f'SELECT {", ".join(chr(34) + c + chr(34) for c in cols)} FROM "{name}"')
            ).all()
            result[name] = {
                "count": len(rows),
                "rows": sorted((tuple(map(repr, r)) for r in rows)),
            }
        db.session.rollback()
        return result

    return take


@pytest.fixture()
def count_queries(engine):
    """Context manager yielding the list of SQL statements run inside it."""

    @contextmanager
    def record():
        statements = []

        def before(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", before)
        try:
            yield statements
        finally:
            event.remove(engine, "before_cursor_execute", before)

    return record
