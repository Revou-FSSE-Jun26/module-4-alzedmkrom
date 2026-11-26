from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, db.Model):
    """Append-only. `message` is written once; `board_id` has no foreign key (DB-NTF-01)."""

    __tablename__ = "notifications"

    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The ten types of backend.md BE-NTF-03 (migration 0003 extends the CHECK).
    type = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    board_id = db.Column(UUID(as_uuid=True), nullable=True)
    is_read = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    user = db.relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        db.CheckConstraint(
            "type IN ('card_assigned', 'card_moved', 'comment_added', 'member_added', 'card_created', 'card_deleted', 'column_deleted', 'board_deleted', 'member_role_changed', 'member_removed')",
            name="type",
        ),
        db.CheckConstraint("char_length(message) BETWEEN 1 AND 500", name="message_length"),
        db.Index(
            "ix_notifications_user_id_created_at",
            "user_id",
            db.text("created_at DESC"),
        ),
        db.Index(
            "ix_notifications_user_id_unread",
            "user_id",
            postgresql_where=db.text("NOT is_read"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Notification {self.id}>"
