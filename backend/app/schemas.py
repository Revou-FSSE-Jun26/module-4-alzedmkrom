"""Shared Marshmallow base classes, field types and input parsing (BE-VAL-01..03)."""
from datetime import timezone

from marshmallow import RAISE, Schema, ValidationError, fields, validate, validates_schema

from app.errors import BadRequest, ValidationFailed

NAME_MAX = 100
TITLE_MAX = 200
DESCRIPTION_MAX = 5000
COMMENT_MAX = 2000
EMAIL_MAX = 254
PASSWORD_MIN = 8
PASSWORD_MAX = 128


class StrictSchema(Schema):
    """Input schemas reject unknown fields (BE-VAL-02)."""

    class Meta:
        unknown = RAISE


class PatchSchema(StrictSchema):
    """PATCH bodies must contain at least one field (BE-VAL-03)."""

    @validates_schema
    def require_one_field(self, data, **kwargs):
        if not data:
            raise ValidationError("At least one field is required.")


class Text(fields.String):
    """String that is stripped before validation."""

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, str):
            value = value.strip()
        return super()._deserialize(value, attr, data, **kwargs)


class Email(Text):
    """Trimmed and lowercased before validation and storage (BE-VAL-03)."""

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        return value.lower()


def to_utc_iso(value):
    """ISO-8601 UTC string ending in Z (BE-ERR-05)."""
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class UTCDateTime(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return to_utc_iso(value)


class PublicUserSchema(Schema):
    """The only user shape exposed to other users (BE-VAL-04)."""

    id = fields.UUID(dump_only=True)
    name = fields.String(dump_only=True)


class PaginationQuerySchema(StrictSchema):
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(load_default=20, validate=validate.Range(min=1, max=100))


def parse(schema_cls, payload):
    """Validate a JSON object or query dict. Raises 400 for a non-object, 422 on field errors."""
    if not isinstance(payload, dict):
        raise BadRequest("Request body must be a JSON object.")
    try:
        return schema_cls().load(payload)
    except ValidationError as exc:
        raise ValidationFailed(details=exc.messages) from None
