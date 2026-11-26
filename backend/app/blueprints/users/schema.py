from marshmallow import Schema, fields, validate

from app.schemas import NAME_MAX, Email, PatchSchema, Text, UTCDateTime


class UserUpdateSchema(PatchSchema):
    name = Text(validate=validate.Length(min=1, max=NAME_MAX))
    email = Email(validate=validate.Email())


class UserSchema(Schema):
    id = fields.UUID(dump_only=True)
    name = fields.String(dump_only=True)
    email = fields.String(dump_only=True)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)
