from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Card(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "cards"

    # `board_id` always equals the board of `column_id`. The composite foreign
    # key below enforces that (DB-SCH-03). There is no separate FK to boards.
    board_id = db.Column(UUID(as_uuid=True), nullable=False)
    column_id = db.Column(UUID(as_uuid=True), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    assignee_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date = db.Column(db.Date, nullable=True)
    # DB-ORD-01: the attribute and API field are `order`, the column is `position`.
    order = db.Column("position", db.Float(53), nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    column = db.relationship("BoardColumn", back_populates="cards")
    assignee = db.relationship("User", foreign_keys=[assignee_id])
    creator = db.relationship("User", foreign_keys=[created_by])
    comments = db.relationship(
        "Comment",
        back_populates="card",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        db.ForeignKeyConstraint(
            ["column_id", "board_id"],
            ["columns.id", "columns.board_id"],
            ondelete="CASCADE",
        ),
        # OD-4, same as columns.position.
        db.CheckConstraint(
            '"position" > 0 AND "position" < \'Infinity\'', name="position"
        ),
        db.CheckConstraint("char_length(title) >= 1", name="title_length"),
        db.CheckConstraint(
            "description IS NULL OR char_length(description) <= 5000",
            name="description_length",
        ),
        db.Index(
            "ix_cards_column_id_position",
            "column_id",
            "position",
            postgresql_where=db.text("deleted_at IS NULL"),
        ),
        db.Index(
            "ix_cards_assignee_id",
            "assignee_id",
            postgresql_where=db.text("assignee_id IS NOT NULL AND deleted_at IS NULL"),
        ),
        db.Index(
            "ix_cards_board_id_created_by",
            "board_id",
            "created_by",
            postgresql_where=db.text("deleted_at IS NULL"),
        ),
        db.Index(
            "ix_cards_board_id_completed_at",
            "board_id",
            "completed_at",
            postgresql_where=db.text("completed_at IS NOT NULL AND deleted_at IS NULL"),
        ),
    )

    @classmethod
    def active(cls):
        """DB-SOFT-02: every live-card query starts here."""
        return cls.query.filter(cls.deleted_at.is_(None))

    def __repr__(self) -> str:
        return f"<Card {self.id}>"
