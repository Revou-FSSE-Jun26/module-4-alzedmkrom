from marshmallow import Schema, ValidationError, fields, validates_schema
from marshmallow.validate import Range

from app.common.validation import DigitsInt, LenientSchema, UTCDateTime

MAX_OFFSET = 1_000_000


class NotificationListQuerySchema(LenientSchema):
    # Unknown query keys are ignored.
    page = DigitsInt(load_default=1, validate=Range(min=1), metadata={"default": 1})
    per_page = DigitsInt(
        load_default=20, validate=Range(min=1, max=100), metadata={"default": 20}
    )

    @validates_schema
    def offset_limit(self, data, **kwargs):
        # (page - 1) * per_page above 1,000,000 is an error on 'page' (Req 13.3).
        if (data["page"] - 1) * data["per_page"] > MAX_OFFSET:
            raise ValidationError("Page offset is too large.", "page")


class NotificationOutSchema(Schema):
    id = fields.UUID(required=True)
    type = fields.String(required=True)
    message = fields.String(required=True)
    board_id = fields.UUID(required=True)
    card_id = fields.UUID(required=True, allow_none=True)
    is_read = fields.Boolean(required=True)
    created_at = UTCDateTime(required=True)


class NotificationPageOutSchema(Schema):
    items = fields.List(fields.Nested(NotificationOutSchema), required=True)
    page = fields.Integer(required=True)
    per_page = fields.Integer(required=True)
    total = fields.Integer(required=True)
