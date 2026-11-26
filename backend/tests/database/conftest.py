"""Fixtures for database tests (DB-TST-01). PostgreSQL 18 only, never SQLite.

TEST_DATABASE_URL is used as is when set. Otherwise a throwaway PostgreSQL 18
cluster is started with initdb and pg_ctl in a temp directory, bound to
127.0.0.1 on a free port, and removed at session end.

The app factory (`app.create_app`) is not used here. It imports every
blueprint, and the blueprints are outside the database layer. While they
still import the removed V3 models, importing `app` fails. The `app` package
is therefore registered as a bare namespace, so `app.models`, `app.extensions`
and `app.seed` load without running `app/__init__.py`. `make_app` builds a
Flask app with the same extensions and the seed command.
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import types
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_DB_ENV = "TEST_DATABASE_URL"
PG_MAJOR = 18


def _register_app_package_without_factory() -> None:
    """Import `app.*` submodules without running `app/__init__.py`."""
    if "app" in sys.modules:
        return
    pkg = types.ModuleType("app")
    pkg.__path__ = [str(BACKEND_DIR / "app")]
    sys.modules["app"] = pkg


_register_app_package_without_factory()


def make_app(url: str):
    """Flask app with the database extensions, migrations and seed command."""
    from flask import Flask

    from app.extensions import db, migrate
    from app.seed import seed_command

    flask_app = Flask("revotask-database-tests")
    flask_app.config.update(
        SQLALCHEMY_DATABASE_URI=url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(flask_app)
    migrate.init_app(
        flask_app,
        db,
        compare_type=True,
        render_as_batch=False,
        transaction_per_migration=True,
    )
    flask_app.cli.add_command(seed_command)
    return flask_app


def migrations_dir() -> str:
    return str(BACKEND_DIR / "migrations")


# ---------------------------------------------------------------------------
# Throwaway PostgreSQL 18 cluster
# ---------------------------------------------------------------------------


def _pg_bin_dir():
    env = os.environ.get("PG_BIN_DIR")
    if env:
        return Path(env)
    found = shutil.which("pg_ctl")
    if found:
        return Path(found).parent
    for root in (
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PostgreSQL",
        Path("/usr/lib/postgresql"),
    ):
        cand = root / str(PG_MAJOR) / "bin"
        if cand.is_dir():
            return cand
    return None


@pytest.fixture(scope="session")
def database_url(tmp_path_factory):
    """URL of the test server. Must be PostgreSQL 18."""
    url = os.environ.get(TEST_DB_ENV)
    if url and url.strip():
        yield url
        return

    bindir = _pg_bin_dir()
    if bindir is None:
        pytest.skip(f"{TEST_DB_ENV} not set and PostgreSQL {PG_MAJOR} binaries not found")

    exe = ".exe" if os.name == "nt" else ""
    data = tmp_path_factory.mktemp("pgdata")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    subprocess.run(
        [str(bindir / f"initdb{exe}"), "-D", str(data), "-U", "postgres",
         "-A", "trust", "-E", "UTF8", "--no-sync"],
        check=True, capture_output=True,
    )
    log = Path(tempfile.gettempdir()) / f"pg_test_{port}.log"
    subprocess.run(
        [str(bindir / f"pg_ctl{exe}"), "-D", str(data), "-w", "-l", str(log),
         "-o", f"-p {port} -h 127.0.0.1 -c fsync=off -c listen_addresses=127.0.0.1",
         "start"],
        check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # no pipes: the postgres children would inherit them and block run()
    try:
        yield f"postgresql://postgres@127.0.0.1:{port}/postgres"
    finally:
        subprocess.run(
            [str(bindir / f"pg_ctl{exe}"), "-D", str(data), "-m", "immediate", "-w", "stop"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        log.unlink(missing_ok=True)


def _assert_pg18(conn) -> None:
    version = int(conn.execute(text("SHOW server_version_num")).scalar())
    if version // 10000 != PG_MAJOR:
        pytest.fail(f"PostgreSQL {PG_MAJOR} required, server_version_num={version}")


@pytest.fixture(scope="session")
def flask_app(database_url):
    """Session app. The schema is built with `upgrade` (same as `flask db upgrade`)."""
    if not database_url.startswith(("postgres://", "postgresql://", "postgresql+")):
        pytest.fail(f"{TEST_DB_ENV} must be a PostgreSQL URL, never SQLite")
    from flask_migrate import upgrade

    from app.extensions import db

    url = database_url.replace("postgres://", "postgresql://", 1)
    flask_app = make_app(url)
    with flask_app.app_context():
        with db.engine.connect() as conn:
            _assert_pg18(conn)
        upgrade(directory=migrations_dir())
    return flask_app


@pytest.fixture(scope="session", autouse=True)
def app_context(flask_app):
    """Models use Flask-SQLAlchemy's `Model.query`, which needs an app context."""
    with flask_app.app_context():
        yield flask_app


@pytest.fixture(scope="session")
def engine(app_context):
    from app.extensions import db

    return db.engine


@pytest.fixture()
def scratch_url(database_url):
    """A new empty database on the same server, dropped after the test."""
    url = make_url(database_url.replace("postgres://", "postgresql://", 1))
    name = f"scratch_{uuid.uuid4().hex[:12]}"
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield url.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


# ---------------------------------------------------------------------------
# Transaction-scoped sessions. Every test rolls back.
# ---------------------------------------------------------------------------


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
    """ORM session joined to the rolled-back transaction (`create_savepoint`)."""
    sess = Session(bind=conn, join_transaction_mode="create_savepoint")
    try:
        yield sess
    finally:
        sess.close()


class expect_failure:
    """Run statements that should fail inside a SAVEPOINT.

    The savepoint is rolled back on any exception, so the outer test transaction
    stays usable. The exception is re-raised.
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
        elif self.nested.is_active:
            self.nested.rollback()
        return False


@pytest.fixture()
def failing():
    """Factory: `with failing(session): ...` rolls back to the savepoint on error."""
    return expect_failure
