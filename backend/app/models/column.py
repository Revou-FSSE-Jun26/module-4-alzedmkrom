from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class BoardColumn(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Table `columns`. The class is BoardColumn because `column` is reserved."""

    __tablename__ = "columns"

    board_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(100), nullable=False)
    # DB-ORD-01: the attribute and API field are `order`, the column is `position`.
    order = db.Column("position", db.Float(53), nullable=False)
    is_done = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    created_by = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    board = db.relationship("Board", back_populates="columns")
    cards = db.relationship(
        "Card",
        back_populates="column",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Card.order",
    )

    __table_args__ = (
        # Target of the composite foreign key on cards (DB-SCH-03).
        db.UniqueConstraint("id", "board_id", name="uq_columns_id_board_id"),
        db.CheckConstraint("char_length(name) >= 1", name="name_length"),
        # OD-4: baseline bound. Rejects NaN (PostgreSQL sorts NaN above Infinity)
        # and +Infinity. Deviates from DB-ORD-01, which lists only `position > 0`.
        db.CheckConstraint(
            '"position" > 0 AND "position" < \'Infinity\'', name="position"
        ),
        # DB-DON-01: at most one done column per board.
        db.Index(
            "uq_columns_board_id_done",
            "board_id",
            unique=True,
            postgresql_where=db.text("is_done"),
        ),
        # DB-ORD-02: non-unique position lookup.
        db.Index("ix_columns_board_id_position", "board_id", "position"),
    )

    def __repr__(self) -> str:
        return f"<BoardColumn {self.id}>"
