from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Board(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "boards"

    name = db.Column(db.String(100), nullable=False)
    # DB-VIS-01: public by default, at the database level as well.
    is_public = db.Column(
        db.Boolean, nullable=False, default=True, server_default=db.true()
    )
    created_by = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    creator = db.relationship("User", foreign_keys=[created_by])
    members = db.relationship(
        "BoardMember",
        back_populates="board",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    columns = db.relationship(
        "BoardColumn",
        back_populates="board",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="BoardColumn.order",
    )

    __table_args__ = (
        db.CheckConstraint("char_length(name) >= 1", name="name_length"),
        db.Index(
            "ix_boards_created_at_public",
            db.text("created_at DESC"),
            postgresql_where=db.text("is_public"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Board {self.id}>"
