"""Response schemas used by more than one blueprint."""

from marshmallow import Schema, fields

from app.common.validation import UTCDateTime


class IdOutSchema(Schema):
    id = fields.UUID(required=True)


class AuthorOutSchema(Schema):
    id = fields.UUID(required=True)
    name = fields.String(required=True)


class ColumnOutSchema(Schema):
    id = fields.UUID(required=True)
    board_id = fields.UUID(required=True)
    title = fields.String(required=True)
    order = fields.Float(required=True)
    created_at = UTCDateTime(required=True)
    updated_at = UTCDateTime(required=True)


class CardOutSchema(Schema):
    id = fields.UUID(required=True)
    title = fields.String(required=True)
    description = fields.String(required=True, allow_none=True)
    assignee_id = fields.UUID(required=True, allow_none=True)
    created_by = fields.UUID(required=True)
    order = fields.Float(required=True)
    completed_at = UTCDateTime(required=True, allow_none=True)
    created_at = UTCDateTime(required=True)
    updated_at = UTCDateTime(required=True)
