"""Shared fixtures, strategies and the field registry for database tests.

Requires a PostgreSQL 16 database named by TEST_DATABASE_URL. SQLite is
never used. The schema is built once per session with `flask db upgrade`.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from hypothesis import HealthCheck, settings, strategies as st
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Hypothesis profile
# ---------------------------------------------------------------------------
settings.register_profile(
    "database",
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
settings.load_profile("database")

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_DB_ENV = "TEST_DATABASE_URL"

# ---------------------------------------------------------------------------
# Field registry: (table, column, min, max, nullable). Matches CHECK limits.
# For nullable fields min is 0 (NULL is allowed in addition to the range).
# ---------------------------------------------------------------------------
FieldSpec = tuple  # (table, column, min_len, max_len, nullable)

FIELD_REGISTRY = [
    ("users", "name", 1, 255, False),
    ("users", "email", 3, 254, False),
    ("boards", "name", 1, 255, False),
    ("columns", "title", 1, 255, False),
    ("cards", "title", 1, 255, False),
    ("cards", "description", 0, 10000, True),
    ("comments", "body", 1, 5000, False),
    ("notifications", "type", 1, 50, False),
    ("notifications", "message", 1, 500, False),
    ("activity_logs", "action", 1, 100, False),
]

# ---------------------------------------------------------------------------
# Session-scoped schema
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    url = os.environ.get(TEST_DB_ENV)
    if not url or not url.strip():
        pytest.skip(f"{TEST_DB_ENV} is not set; PostgreSQL 16 is required")
    if not url.startswith(("postgres://", "postgresql://", "postgresql+")):
        pytest.fail(f"{TEST_DB_ENV} must be a PostgreSQL URL, never SQLite")

    os.environ["DATABASE_URL"] = url
    from flask_migrate import upgrade

    from app import create_app

    flask_app = create_app()
    with flask_app.app_context():
        from app.extensions import db

        with db.engine.connect() as conn:
            version = int(conn.exec_driver_sql("SHOW server_version_num").scalar())
        if version // 10000 != 16:
            pytest.fail(f"PostgreSQL 16 required, server_version_num={version}")
        upgrade(directory=str(BACKEND_DIR / "migrations"))  # == `flask db upgrade`
    return flask_app


@pytest.fixture(scope="session")
def engine(app):
    from app.extensions import db

    with app.app_context():
        yield db.engine


@pytest.fixture()
def conn(engine):
    """A connection inside an outer transaction that is always rolled back."""
    connection = engine.connect()
    outer = connection.begin()
    try:
        yield connection
    finally:
        outer.rollback()
        connection.close()


@pytest.fixture()
def session(conn):
    """ORM session joined to the rolled-back transaction.

    `create_savepoint` keeps commit()/rollback() inside the outer transaction.
    """
    sess = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield sess
    finally:
        sess.close()


class expect_failure:
    """Run statements expected to fail inside a SAVEPOINT.

    The savepoint is rolled back on any exception, so the enclosing
    transaction stays usable. The exception is re-raised.

        with pytest.raises(IntegrityError):
            with expect_failure(session):
                session.add(bad); session.flush()
    """

    def __init__(self, sess):
        self.sess = sess
        self.nested = None

    def __enter__(self):
        self.nested = self.sess.begin_nested()
        return self.sess

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.nested.commit()
        else:
            if self.nested.is_active:
                self.nested.rollback()
        return False


@pytest.fixture()
def failing():
    """Factory: `failing(session)` returns an `expect_failure` context."""
    return expect_failure


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------
# PostgreSQL text cannot hold NUL; surrogates cannot be encoded as UTF-8.
_PG_ALPHABET = st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00")
_WS = st.sampled_from([" ", "\t", "\n", "\r", "\u00a0", "\u2003", "\u3000"])
_NON_BMP = st.characters(min_codepoint=0x10000, max_codepoint=0x10FFFF, blacklist_categories=("Cs",))

text_with_edge_chars = st.text(st.one_of(_PG_ALPHABET, _WS, _NON_BMP), min_size=0, max_size=50)


def text_of_length(min_len, max_len):
    """Text whose length in code points is within [min_len, max_len]."""
    return st.text(st.one_of(_PG_ALPHABET, _WS, _NON_BMP), min_size=min_len, max_size=max_len)


floats_with_specials = st.floats(allow_nan=True, allow_infinity=True)
finite_positive_floats = st.floats(
    min_value=5e-324, max_value=1e300, allow_nan=False, allow_infinity=False
)

aware_datetimes = st.datetimes(
    min_value=datetime(1970, 1, 2),
    max_value=datetime(9000, 1, 1),
    # Fixed offsets only: st.timezones() needs tzdata, absent on some hosts.
    timezones=st.just(timezone.utc)
    | st.builds(
        lambda m: timezone(timedelta(minutes=m)),
        st.integers(-12 * 60, 14 * 60),
    ),
)


@st.composite
def board_graphs(draw, max_users=4, max_columns=4, max_cards=6):
    """Plain-data board graph; persist it with `persist_board_graph`.

    Returns dict with users, board, members, columns, cards. Cross references
    use list indexes so the graph is valid by construction.
    """
    n_users = draw(st.integers(1, max_users))
    n_cols = draw(st.integers(0, max_columns))
    users = [
        {"id": uuid.uuid4(), "name": draw(text_of_length(1, 40)) or "u"}
        for _ in range(n_users)
    ]
    owner = draw(st.integers(0, n_users - 1))
    members = sorted(draw(st.sets(st.integers(0, n_users - 1), max_size=n_users)) | {owner})
    columns = [
        {
            "id": uuid.uuid4(),
            "title": draw(text_of_length(1, 40)),
            "order": draw(finite_positive_floats),
        }
        for _ in range(n_cols)
    ]
    cards = []
    if n_cols:
        for _ in range(draw(st.integers(0, max_cards))):
            cards.append(
                {
                    "id": uuid.uuid4(),
                    "column": draw(st.integers(0, n_cols - 1)),
                    "title": draw(text_of_length(1, 40)),
                    "description": draw(st.none() | text_of_length(0, 100)),
                    "order": draw(finite_positive_floats),
                    "creator": draw(st.integers(0, n_users - 1)),
                    "assignee": draw(st.none() | st.integers(0, n_users - 1)),
                }
            )
    return {
        "users": users,
        "board": {
            "id": uuid.uuid4(),
            "name": draw(text_of_length(1, 40)),
            "owner": owner,
        },
        "members": members,
        "columns": columns,
        "cards": cards,
    }


def persist_board_graph(sess, graph):
    """Insert a `board_graphs` value and flush. Returns the board id."""
    from app.models.board import Board, BoardMember
    from app.models.card import Card
    from app.models.column import BoardColumn
    from app.models.user import User

    users = graph["users"]
    for i, u in enumerate(users):
        sess.add(
            User(
                id=u["id"],
                name=u["name"],
                email=f"u{i}-{u['id'].hex}@example.com",
                password_hash="x",
            )
        )
    sess.flush()
    b = graph["board"]
    sess.add(Board(id=b["id"], name=b["name"], owner_id=users[b["owner"]]["id"]))
    sess.flush()
    for i in graph["members"]:
        sess.add(
            BoardMember(
                board_id=b["id"],
                user_id=users[i]["id"],
                role="admin" if i == b["owner"] else "member",
            )
        )
    for c in graph["columns"]:
        sess.add(BoardColumn(id=c["id"], board_id=b["id"], title=c["title"], order=c["order"]))
    sess.flush()
    for c in graph["cards"]:
        sess.add(
            Card(
                id=c["id"],
                column_id=graph["columns"][c["column"]]["id"],
                created_by=users[c["creator"]]["id"],
                assignee_id=None if c["assignee"] is None else users[c["assignee"]]["id"],
                title=c["title"],
                description=c["description"],
                order=c["order"],
            )
        )
    sess.flush()
    return b["id"]
