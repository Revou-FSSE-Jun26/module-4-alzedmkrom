from marshmallow import Schema, ValidationError, fields
from marshmallow.validate import Length

from app.common.schemas import AuthorOutSchema
from app.common.validation import LenientSchema, Text, UTCDateTime


def has_non_whitespace(value: str) -> None:
    if not any(not ch.isspace() for ch in value):
        raise ValidationError("Must contain a non-whitespace character.")


class CommentSchema(LenientSchema):
    content = Text(required=True, validate=[Length(1, 5000), has_non_whitespace])


class CommentOutSchema(Schema):
    id = fields.UUID(required=True)
    card_id = fields.UUID(required=True)
    content = fields.String(required=True, attribute="body")
    author = fields.Nested(AuthorOutSchema, required=True)
    created_at = UTCDateTime(required=True)
    updated_at = UTCDateTime(required=True)
