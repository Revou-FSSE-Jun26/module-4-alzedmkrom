"""Flask application factory."""
import os

from flask import Flask

from app.db_config import engine_options, normalize_database_url, verify_connection
from app.extensions import db, migrate


def skip_empty_revision(context, revision, directives):
    """Req 10.5. Write no migration file when autogenerate finds no changes."""
    if getattr(context.config.cmd_opts, "autogenerate", False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []


def create_app(verify_db: bool = True) -> Flask:
    app = Flask(__name__)
    uri = normalize_database_url(os.environ.get("DATABASE_URL"))  # raises before any engine exists
    app.config.update(
        SQLALCHEMY_DATABASE_URI=uri,
        SQLALCHEMY_ENGINE_OPTIONS=engine_options(),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    migrate.init_app(
        app,
        db,
        compare_type=True,
        render_as_batch=False,
        transaction_per_migration=True,
        process_revision_directives=skip_empty_revision,
    )
    from app import models  # noqa: F401  (register tables)

    if verify_db:
        with app.app_context():
            verify_connection(db.engine)
    return app
