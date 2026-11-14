from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Card(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "cards"

    column_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("columns.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignee_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)
    order = db.Column(db.Float, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    column = db.relationship("BoardColumn", back_populates="cards")
    assignee = db.relationship("User", foreign_keys=[assignee_id])
    creator = db.relationship("User", foreign_keys=[created_by])
    comments = db.relationship("Comment", back_populates="card", passive_deletes=True)

    __table_args__ = (
        db.CheckConstraint("char_length(title) BETWEEN 1 AND 255", name="title_length"),
        db.CheckConstraint(
            "description IS NULL OR char_length(description) <= 10000",
            name="description_length",
        ),
        db.CheckConstraint(
            "\"order\" > 0 AND \"order\" < 'Infinity'", name="order_positive_finite"
        ),
        db.Index("ix_cards_column_id_order", "column_id", "order"),
        db.Index("ix_cards_assignee_id", "assignee_id"),
        db.Index("ix_cards_completed_at", "completed_at"),
    )

    def __repr__(self) -> str:
        return f"<Card {self.id}>"
