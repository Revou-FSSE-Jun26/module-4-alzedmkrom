"""`flask seed` tests on a scratch PostgreSQL 18 database (DB-SEED-01).

Each test gets its own empty database, so the seed can commit without touching
the session database.
"""

from flask_migrate import upgrade
from sqlalchemy import text

from tests.database.conftest import make_app, migrations_dir

EXPECTED_COUNTS = {
    "users": 3,
    "boards": 2,
    "board_members": 3,
    "columns": 4,
    "cards": 6,
    "comments": 2,
}


def _counts(engine):
    with engine.connect() as conn:
        return {
            table: conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in EXPECTED_COUNTS
        }


def _migrated_app(scratch_url):
    from app.extensions import db

    app = make_app(scratch_url)
    ctx = app.app_context()
    ctx.push()
    upgrade(directory=migrations_dir())
    return app, ctx, db


def test_seed_writes_the_demo_data_and_is_idempotent(scratch_url, monkeypatch):
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("SEED_PASSWORD", raising=False)
    app, ctx, db = _migrated_app(scratch_url)
    try:
        runner = app.test_cli_runner()
        first = runner.invoke(args=["seed"])
        assert first.exit_code == 0, first.output
        assert "Seeding finished." in first.output
        after_first = _counts(db.engine)
        assert after_first == EXPECTED_COUNTS

        second = runner.invoke(args=["seed"])
        assert second.exit_code == 0, second.output
        assert _counts(db.engine) == after_first
    finally:
        ctx.pop()


def test_seed_guest_has_no_membership_and_sandbox_is_private(scratch_url, monkeypatch):
    monkeypatch.delenv("FLASK_ENV", raising=False)
    app, ctx, db = _migrated_app(scratch_url)
    try:
        assert app.test_cli_runner().invoke(args=["seed"]).exit_code == 0
        with db.engine.connect() as conn:
            carol_memberships = conn.execute(text(
                "SELECT count(*) FROM board_members bm JOIN users u ON u.id = bm.user_id "
                "WHERE u.email = 'carol@revotask.test'"
            )).scalar_one()
            private = conn.execute(text(
                "SELECT is_public FROM boards WHERE name = 'Private Sandbox'"
            )).scalar_one()
            done_completed = conn.execute(text(
                "SELECT count(*) FROM cards c JOIN columns col ON col.id = c.column_id "
                "WHERE col.is_done AND c.completed_at IS NOT NULL"
            )).scalar_one()
        assert carol_memberships == 0
        assert private is False
        assert done_completed == 1
    finally:
        ctx.pop()


def test_seed_refuses_production_without_force(scratch_url, monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    app, ctx, db = _migrated_app(scratch_url)
    try:
        refused = app.test_cli_runner().invoke(args=["seed"])
        assert refused.exit_code != 0
        assert "without --force" in refused.output
        assert _counts(db.engine)["users"] == 0

        forced = app.test_cli_runner().invoke(args=["seed", "--force"])
        assert forced.exit_code == 0, forced.output
        assert _counts(db.engine) == EXPECTED_COUNTS
    finally:
        ctx.pop()
