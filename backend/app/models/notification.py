from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, db.Model):
    __tablename__ = "notifications"

    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    board_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
    )
    card_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cards.id", ondelete="SET NULL"),
        nullable=True,
    )
    type = db.Column(db.Text, nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
    )

    __table_args__ = (
        db.CheckConstraint("char_length(type) BETWEEN 1 AND 50", name="type_length"),
        db.CheckConstraint(
            "char_length(message) BETWEEN 1 AND 500", name="message_length"
        ),
        db.Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Notification {self.id}>"
