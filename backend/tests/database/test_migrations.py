"""Migration tests (DB-MIG-01, DB-MIG-02).

The round trip runs on a scratch database, so the session database is never
downgraded. Snapshots compare catalog contents as sets. Column order is not
compared because ALTER appends columns.
"""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask_migrate import downgrade, upgrade
from sqlalchemy import text

from tests.database.conftest import make_app, migrations_dir

HEAD = "0002_v4_schema"
BASE_V3 = "0001_initial_schema"


def _snapshot(engine):
    with engine.connect() as conn:
        return {
            "columns": sorted(
                tuple(r) for r in conn.execute(text(
                    "SELECT table_name, column_name, data_type, character_maximum_length, "
                    "is_nullable, column_default FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
                ))
            ),
            # NOT NULL constraints (contype 'n') are left out. PostgreSQL 18 names
            # them after the column, and RENAME COLUMN keeps the old name. The
            # nullability itself is still compared through "columns".
            "constraints": sorted(
                tuple(r) for r in conn.execute(text(
                    "SELECT conrelid::regclass::text, conname, contype, "
                    "pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE connamespace = 'public'::regnamespace AND contype <> 'n'"
                ))
            ),
            "indexes": sorted(
                tuple(r) for r in conn.execute(text(
                    "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'"
                ))
            ),
            "triggers": sorted(
                tuple(r) for r in conn.execute(text(
                    "SELECT tgname, tgrelid::regclass::text FROM pg_trigger WHERE NOT tgisinternal"
                ))
            ),
            "functions": sorted(
                tuple(r) for r in conn.execute(text(
                    "SELECT proname FROM pg_proc WHERE pronamespace = 'public'::regnamespace"
                ))
            ),
        }


def test_single_migration_head_with_one_parent():
    script = ScriptDirectory(migrations_dir())
    assert script.get_heads() == [HEAD]
    assert script.get_revision(HEAD).down_revision == BASE_V3


def test_models_match_the_migrated_schema(engine):
    """Autogenerate sees no difference between the models and the migrated database."""
    from app.extensions import db

    with engine.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_type": True})
        differences = compare_metadata(context, db.metadata)
    assert differences == []


def _difference(expected, actual):
    """Per catalog group: (only in expected, only in actual). Empty when equal."""
    report = {}
    for group in expected:
        if expected[group] != actual[group]:
            report[group] = (
                sorted(set(expected[group]) - set(actual[group])),
                sorted(set(actual[group]) - set(expected[group])),
            )
    return report


def test_downgrade_to_0001_restores_the_v3_shape_and_upgrade_reapplies_v4(scratch_url):
    app = make_app(scratch_url)
    from app.extensions import db

    with app.app_context():
        upgrade(directory=migrations_dir(), revision=BASE_V3)
        v3 = _snapshot(db.engine)

        upgrade(directory=migrations_dir(), revision=HEAD)
        v4 = _snapshot(db.engine)

        downgrade(directory=migrations_dir(), revision=BASE_V3)
        assert _difference(v3, _snapshot(db.engine)) == {}

        upgrade(directory=migrations_dir(), revision=HEAD)
        assert _difference(v4, _snapshot(db.engine)) == {}
