from marshmallow import Schema, fields, validate

from app.schemas import (
    NAME_MAX,
    Email,
    PaginationQuerySchema,
    PatchSchema,
    StrictSchema,
    Text,
    UTCDateTime,
)

ROLES = ["member", "admin"]


class BoardCreateSchema(StrictSchema):
    name = Text(required=True, validate=validate.Length(min=1, max=NAME_MAX))
    is_public = fields.Boolean(load_default=True)


class BoardUpdateSchema(PatchSchema):
    name = Text(validate=validate.Length(min=1, max=NAME_MAX))
    is_public = fields.Boolean()


class BoardListQuerySchema(PaginationQuerySchema):
    scope = fields.String(validate=validate.OneOf(["mine", "public"]))


class MemberAddSchema(StrictSchema):
    email = Email(required=True, validate=validate.Email())
    role = fields.String(required=True, validate=validate.OneOf(ROLES))


class MemberUpdateSchema(StrictSchema):
    role = fields.String(required=True, validate=validate.OneOf(ROLES))


class BoardSchema(Schema):
    id = fields.UUID(dump_only=True)
    name = fields.String(dump_only=True)
    is_public = fields.Boolean(dump_only=True)
    created_by = fields.UUID(dump_only=True, allow_none=True)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)


class MemberSchema(Schema):
    user_id = fields.UUID(dump_only=True)
    name = fields.String(dump_only=True)
    email = fields.String(dump_only=True, allow_none=True)
    role = fields.String(dump_only=True)
    created_at = UTCDateTime(dump_only=True)
