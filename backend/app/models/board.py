from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import (
    CreatedAtMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Board(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    __tablename__ = "boards"
    name = db.Column(db.Text, nullable=False)
    owner_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    owner = db.relationship("User")
    members = db.relationship("BoardMember", back_populates="board", passive_deletes=True)
    columns = db.relationship(
        "BoardColumn",
        back_populates="board",
        passive_deletes=True,
        order_by="BoardColumn.order",
    )

    __table_args__ = (
        db.CheckConstraint("char_length(name) BETWEEN 1 AND 255", name="name_length"),
    )


class BoardMember(CreatedAtMixin, db.Model):
    __tablename__ = "board_members"
    board_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("boards.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role = db.Column(db.Text, nullable=False)

    board = db.relationship("Board", back_populates="members")
    user = db.relationship("User")

    __table_args__ = (
        db.CheckConstraint("role IN ('member', 'admin')", name="role_valid"),
        db.Index("ix_board_members_user_id", "user_id"),
    )
