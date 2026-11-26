from marshmallow import Schema, fields

from app.schemas import UTCDateTime


class NotificationSchema(Schema):
    id = fields.UUID(dump_only=True)
    type = fields.String(dump_only=True)
    message = fields.String(dump_only=True)
    board_id = fields.UUID(dump_only=True, allow_none=True)
    is_read = fields.Boolean(dump_only=True)
    created_at = UTCDateTime(dump_only=True)
