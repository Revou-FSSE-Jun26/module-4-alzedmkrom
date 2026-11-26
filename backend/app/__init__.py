"""Flask application factory (BE-STR-01: blueprints are registered only here)."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from app.auth_utils import register_jwt_callbacks
from app.config import compile_origins, load_settings
from app.db_config import engine_options, normalize_database_url, verify_connection
from app.errors import register_error_handlers
from app.extensions import db, jwt, migrate

BACKEND_DIR = Path(__file__).resolve().parent.parent


def skip_empty_revision(context, revision, directives):
    """Write no migration file when autogenerate finds no changes."""
    if getattr(context.config.cmd_opts, "autogenerate", False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []


def health():
    return jsonify({"status": "ok"}), 200


def register_blueprints(app: Flask) -> None:
    from app.blueprints.analytics.routes import bp as analytics_bp
    from app.blueprints.auth.routes import bp as auth_bp
    from app.blueprints.boards.routes import bp as boards_bp
    from app.blueprints.cards.routes import bp as cards_bp
    from app.blueprints.columns.routes import bp as columns_bp
    from app.blueprints.comments.routes import bp as comments_bp
    from app.blueprints.notifications.routes import bp as notifications_bp
    from app.blueprints.users.routes import bp as users_bp

    for blueprint in (
        auth_bp,
        users_bp,
        boards_bp,
        columns_bp,
        cards_bp,
        comments_bp,
        notifications_bp,
        analytics_bp,
    ):
        app.register_blueprint(blueprint)


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
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=settings.jwt_expires_minutes),
        MAX_CONTENT_LENGTH=1_048_576,
    )
    if settings.secret_key:
        app.config["SECRET_KEY"] = settings.secret_key

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
    app.add_url_rule("/api/health", endpoint="health", view_func=health, methods=["GET"])

    from app.seed import seed_command

    app.cli.add_command(seed_command)

    if verify_db:
        with app.app_context():
            verify_connection(db.engine)
    return app
