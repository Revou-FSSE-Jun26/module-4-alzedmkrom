"""Flask application factory."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from app.blueprints import register_blueprints
from app.common.auth import register_jwt_callbacks
from app.common.errors import register_error_handlers
from app.config import compile_origins, load_settings
from app.db_config import engine_options, normalize_database_url, verify_connection
from app.extensions import db, jwt, migrate

BACKEND_DIR = Path(__file__).resolve().parent.parent


def skip_empty_revision(context, revision, directives):
    """Req 10.5. Write no migration file when autogenerate finds no changes."""
    if getattr(context.config.cmd_opts, "autogenerate", False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []


def create_app(verify_db: bool = True) -> Flask:
    load_dotenv(BACKEND_DIR / ".env", override=False)  # process env wins
    app = Flask(__name__)
    uri = normalize_database_url(os.environ.get("DATABASE_URL"))  # raises before any engine exists
    settings = load_settings(os.environ)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=uri,
        SQLALCHEMY_ENGINE_OPTIONS={**engine_options(), "hide_parameters": True},
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=settings.jwt_secret_key,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(seconds=settings.jwt_access_token_expires),
        MAX_CONTENT_LENGTH=1_048_576,
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
    jwt.init_app(app)
    register_jwt_callbacks(jwt)
    CORS(
        app,
        resources={
            r"/*": {
                "origins": compile_origins(settings.cors_origins),
                "methods": ["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Authorization", "Content-Type"],
                "supports_credentials": False,
                "always_send": False,
            }
        },
    )
    register_error_handlers(app)
    from app import models  # noqa: F401  (register tables)

    register_blueprints(app)
    from app.seed import seed_command

    app.cli.add_command(seed_command)

    if verify_db:
        with app.app_context():
            verify_connection(db.engine)
    return app
