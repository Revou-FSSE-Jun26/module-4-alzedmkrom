from marshmallow import fields

from app.common.validation import StrictSchema


class HealthOutSchema(StrictSchema):
    status = fields.String(required=True)
