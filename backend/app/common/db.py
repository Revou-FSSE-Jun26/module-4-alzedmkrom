from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.common.errors import Conflict, ValidationFailed
from app.extensions import db
from app.models.board import Board


def lock_board(board_id: UUID) -> None:
    """Serialize order-sensitive and membership-changing writes (D7)."""
    db.session.execute(
        select(Board.id).where(Board.id == board_id).with_for_update()
    ).first()


def commit_or_conflict() -> None:
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        code = getattr(e.orig, "pgcode", None)
        if code == "23505":
            raise Conflict("Resource already exists") from None
        if isinstance(code, str) and code.startswith("23"):
            raise ValidationFailed("Request violates a data constraint") from None
        raise
