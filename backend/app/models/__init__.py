"""Import every model so that its table is registered on ``db.metadata``.

Alembic autogenerate and ``db.create_all`` only see tables whose model
modules have been imported.
"""

from app.models.user import User
from app.models.board import Board, BoardMember
from app.models.column import BoardColumn
from app.models.card import Card
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.activity_log import ActivityLog

__all__ = [
    "User",
    "Board",
    "BoardMember",
    "BoardColumn",
    "Card",
    "Comment",
    "Notification",
    "ActivityLog",
]
