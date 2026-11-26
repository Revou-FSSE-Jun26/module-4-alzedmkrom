"""Shared column mixins (DB-CNV-03, DB-CNV-04, DB-CNV-05).

`updated_at` is refreshed by the database trigger `set_updated_at()` created in
migration 0002, not by the ORM. `server_onupdate=FetchedValue()` makes the ORM
re-read the value after an UPDATE.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


class UUIDPrimaryKeyMixin:
    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("gen_random_uuid()"),
    )


class CreatedAtMixin:
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )


class TimestampMixin(CreatedAtMixin):
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        server_onupdate=db.FetchedValue(),
    )


class SoftDeleteMixin:
    """Used by Card only (DB-SOFT-01). Other tables are hard-deleted."""

    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)
