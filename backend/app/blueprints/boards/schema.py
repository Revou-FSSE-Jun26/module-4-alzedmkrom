from marshmallow import Schema, fields
from marshmallow.validate import Length, OneOf

from app.common.schemas import CardOutSchema, ColumnOutSchema
from app.common.validation import Email, LenientSchema, Text, UTCDateTime


class BoardCreateSchema(LenientSchema):
    name = Text(required=True, validate=Length(1, 255))


class BoardUpdateSchema(BoardCreateSchema):
    pass


class BoardOutSchema(Schema):
    id = fields.UUID(required=True)
    name = fields.String(required=True)
    owner_id = fields.UUID(required=True)
    role = fields.String(required=True)
    created_at = UTCDateTime(required=True)
    updated_at = UTCDateTime(required=True)


class ColumnWithCardsOutSchema(ColumnOutSchema):
    cards = fields.List(fields.Nested(CardOutSchema), required=True)


class BoardDetailOutSchema(BoardOutSchema):
    columns = fields.List(fields.Nested(ColumnWithCardsOutSchema), required=True)

_ROLES = ["member", "admin"]


class MemberAddSchema(LenientSchema):
    email = Email(required=True)
    role = fields.String(validate=OneOf(_ROLES), load_default="member")


class MemberRoleSchema(LenientSchema):
    role = fields.String(required=True, validate=OneOf(_ROLES))


class MemberOutSchema(Schema):
    user_id = fields.UUID(required=True)
    name = fields.String(required=True)
    email = fields.String(required=True)
    role = fields.String(required=True)
    created_at = UTCDateTime(required=True)


class MemberRemovedOutSchema(Schema):
    user_id = fields.UUID(required=True)
