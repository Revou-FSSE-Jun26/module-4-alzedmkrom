"""Transaction boundary for write services (BE-SVC-01) and board locks (DB-MEM-02, BE-ORD-02)."""
import functools

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.errors import Conflict
from app.extensions import db
from app.models import Board

UNIQUE_VIOLATION = "23505"


def transactional(fn):
    """Commit once when `fn` returns; roll back and re-raise on any exception."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            if getattr(exc.orig, "pgcode", None) == UNIQUE_VIOLATION:
                raise Conflict("The change conflicts with existing data.") from None
            raise
        except Exception:
            db.session.rollback()
            raise
        return result

    return wrapper


def lock_board(board_id):
    """Row-lock the board so order-sensitive and membership writes run one at a time."""
    db.session.execute(select(Board.id).where(Board.id == board_id).with_for_update()).first()
