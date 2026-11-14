from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class ActivityLog(UUIDPrimaryKeyMixin, CreatedAtMixin, db.Model):
    __tablename__ = "activity_logs"

    board_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    card_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cards.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = db.Column(db.Text, nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            "char_length(action) BETWEEN 1 AND 100", name="action_length"
        ),
        db.Index("ix_activity_logs_board_id_created_at", "board_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ActivityLog {self.id}>"
