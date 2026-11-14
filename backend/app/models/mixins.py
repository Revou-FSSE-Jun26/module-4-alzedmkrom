import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db


def _tstz(**kw):
    return db.Column(db.DateTime(timezone=True), **kw)


class UUIDPrimaryKeyMixin:
    id = db.Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("gen_random_uuid()"),
    )


class CreatedAtMixin:
    created_at = _tstz(nullable=False, server_default=db.func.now())


class TimestampMixin(CreatedAtMixin):
    # Maintained by trigger set_updated_at(); FetchedValue makes the ORM re-read it.
    updated_at = _tstz(
        nullable=False,
        server_default=db.func.now(),
        server_onupdate=db.FetchedValue(),
    )


class SoftDeleteMixin:
    deleted_at = _tstz(nullable=True)

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.deleted_at = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
