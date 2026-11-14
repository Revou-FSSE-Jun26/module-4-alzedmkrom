from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Comment(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "comments"

    card_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    body = db.Column(db.Text, nullable=False)

    card = db.relationship("Card", back_populates="comments")
    author = db.relationship("User")

    __table_args__ = (
        db.CheckConstraint(
            r"body ~ '\S' AND char_length(body) <= 5000", name="body_valid"
        ),
        db.CheckConstraint("updated_at >= created_at", name="updated_after_created"),
        db.Index("ix_comments_card_id", "card_id"),
    )

    def __repr__(self) -> str:
        return f"<Comment {self.id}>"
