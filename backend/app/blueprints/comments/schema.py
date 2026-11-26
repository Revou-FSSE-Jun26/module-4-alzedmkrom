from marshmallow import Schema, fields, validate

from app.schemas import COMMENT_MAX, PublicUserSchema, StrictSchema, Text, UTCDateTime


class CommentCreateSchema(StrictSchema):
    content = Text(required=True, validate=validate.Length(min=1, max=COMMENT_MAX))


class CommentUpdateSchema(StrictSchema):
    content = Text(required=True, validate=validate.Length(min=1, max=COMMENT_MAX))


class CommentSchema(Schema):
    id = fields.UUID(dump_only=True)
    content = fields.String(dump_only=True)
    author = fields.Nested(PublicUserSchema, dump_only=True, allow_none=True)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)
