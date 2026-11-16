"""Blueprint registration."""
from flask import Flask


def register_blueprints(app: Flask) -> None:
    from app.blueprints.analytics.routes import bp as analytics_bp
    from app.blueprints.auth.routes import bp as auth_bp
    from app.blueprints.boards.routes import bp as boards_bp
    from app.blueprints.cards.routes import bp as cards_bp
    from app.blueprints.columns.routes import bp as columns_bp
    from app.blueprints.comments.routes import bp as comments_bp
    from app.blueprints.health.routes import bp as health_bp
    from app.blueprints.notifications.routes import bp as notifications_bp
    from app.blueprints.users.routes import bp as users_bp

    for bp in (
        auth_bp,
        users_bp,
        boards_bp,
        columns_bp,
        cards_bp,
        comments_bp,
        notifications_bp,
        analytics_bp,
        health_bp,
    ):
        app.register_blueprint(bp)
