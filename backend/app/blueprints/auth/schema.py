from marshmallow import fields, validate

from app.common.validation import Email, LenientSchema, StrictSchema, Text, UTCDateTime


class RegisterSchema(StrictSchema):
    name = Text(required=True, validate=validate.Length(min=1, max=255))
    email = Email(required=True)
    # Passwords are never trimmed.
    password = Text(required=True, validate=validate.Length(min=8, max=128))


class LoginSchema(LenientSchema):
    # Only presence and type are checked; the service normalizes the email.
    email = Text(required=True)
    password = Text(required=True)


class RegisterOutSchema(StrictSchema):
    id = fields.UUID(required=True)
    name = fields.String(required=True)
    email = fields.String(required=True)
    created_at = UTCDateTime(required=True)


class UserBriefOutSchema(StrictSchema):
    id = fields.UUID(required=True)
    name = fields.String(required=True)
    email = fields.String(required=True)


class LoginOutSchema(StrictSchema):
    access_token = fields.String(required=True)
    token_type = fields.String(required=True)
    expires_in = fields.Integer(required=True)
    user = fields.Nested(UserBriefOutSchema, required=True)
