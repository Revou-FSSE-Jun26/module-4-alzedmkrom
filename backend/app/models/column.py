from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class BoardColumn(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "columns"

    board_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = db.Column(db.Text, nullable=False)
    order = db.Column(db.Float, nullable=False)

    board = db.relationship("Board", back_populates="columns")
    cards = db.relationship(
        "Card",
        back_populates="column",
        passive_deletes=True,
        order_by="Card.order",
    )

    __table_args__ = (
        db.CheckConstraint("char_length(title) BETWEEN 1 AND 255", name="title_length"),
        db.CheckConstraint(
            '"order" > 0 AND "order" < \'Infinity\'', name="order_positive"
        ),
        db.Index("ix_columns_board_id_order", "board_id", "order"),  # Req 9.3
    )
