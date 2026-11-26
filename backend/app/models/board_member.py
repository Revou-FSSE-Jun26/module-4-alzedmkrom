from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import CreatedAtMixin


class BoardMember(CreatedAtMixin, db.Model):
    """A user's role on one board (DB-MEM-01). Append-only: no `updated_at`.

    The composite primary key (board_id, user_id) allows one role per user per
    board. A user with no row is a Guest and has no stored value.
    """

    __tablename__ = "board_members"

    board_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("boards.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role = db.Column(db.String(10), nullable=False)
    added_by = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    board = db.relationship("Board", back_populates="members")
    user = db.relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        db.CheckConstraint("role IN ('member', 'admin')", name="role"),
        db.Index("ix_board_members_user_id", "user_id"),
    )
