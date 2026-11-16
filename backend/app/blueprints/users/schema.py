from marshmallow import ValidationError, fields, validate, validates_schema

from app.common.validation import Email, StrictSchema, Text, UTCDateTime


class ProfileUpdateSchema(StrictSchema):
    name = Text(validate=validate.Length(min=1, max=255))
    email = Email()

    @validates_schema
    def at_least_one(self, data, **kwargs):
        # {} gives 400 (Req 3.4). Unknown fields are rejected by StrictSchema (Req 3.3).
        if not data:
            raise ValidationError("Provide name, email or both", "_schema")


class ProfileOutSchema(StrictSchema):
    id = fields.UUID(required=True)
    name = fields.String(required=True)
    email = fields.String(required=True)
    created_at = UTCDateTime(required=True)
    updated_at = UTCDateTime(required=True)
