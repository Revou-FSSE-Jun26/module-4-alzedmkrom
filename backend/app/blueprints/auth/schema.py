from marshmallow import fields, validate

from app.schemas import EMAIL_MAX, NAME_MAX, PASSWORD_MAX, PASSWORD_MIN, Email, StrictSchema, Text


class RegisterSchema(StrictSchema):
    name = Text(required=True, validate=validate.Length(min=1, max=NAME_MAX))
    email = Email(required=True, validate=[validate.Email(), validate.Length(max=EMAIL_MAX)])
    password = fields.String(
        required=True, validate=validate.Length(min=PASSWORD_MIN, max=PASSWORD_MAX)
    )


class LoginSchema(StrictSchema):
    email = Email(required=True, validate=validate.Email())
    password = fields.String(required=True)
