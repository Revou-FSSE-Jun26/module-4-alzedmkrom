from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Comment(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Hard-deleted (DB-CNV-05). Removed when its card is removed."""

    __tablename__ = "comments"

    card_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    card = db.relationship("Card", back_populates="comments")
    author = db.relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        db.CheckConstraint("char_length(content) BETWEEN 1 AND 2000", name="content_length"),
        db.CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        db.Index("ix_comments_card_id_created_at", "card_id", "created_at"),
        db.Index("ix_comments_created_by", "created_by"),
    )

    def __repr__(self) -> str:
        return f"<Comment {self.id}>"
