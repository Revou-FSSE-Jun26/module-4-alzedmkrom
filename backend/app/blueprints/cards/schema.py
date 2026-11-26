from marshmallow import Schema, fields, validate

from app.schemas import (
    DESCRIPTION_MAX,
    TITLE_MAX,
    PaginationQuerySchema,
    PatchSchema,
    PublicUserSchema,
    StrictSchema,
    Text,
    UTCDateTime,
)


class CardCreateSchema(StrictSchema):
    title = Text(required=True, validate=validate.Length(min=1, max=TITLE_MAX))
    description = Text(allow_none=True, validate=validate.Length(max=DESCRIPTION_MAX))
    assignee_id = fields.UUID(allow_none=True)
    due_date = fields.Date(allow_none=True)


class CardUpdateSchema(PatchSchema):
    title = Text(validate=validate.Length(min=1, max=TITLE_MAX))
    description = Text(allow_none=True, validate=validate.Length(max=DESCRIPTION_MAX))
    assignee_id = fields.UUID(allow_none=True)
    due_date = fields.Date(allow_none=True)


class CardPositionSchema(StrictSchema):
    column_id = fields.UUID(required=True)
    order = fields.Float(required=True, validate=validate.Range(min=0, min_inclusive=False))


class AssignedCardsQuerySchema(PaginationQuerySchema):
    assignee = fields.String(required=True, validate=validate.OneOf(["me"]))
    board_id = fields.UUID()
    done = fields.Boolean()


class CardSchema(Schema):
    id = fields.UUID(dump_only=True)
    board_id = fields.UUID(dump_only=True)
    column_id = fields.UUID(dump_only=True)
    title = fields.String(dump_only=True)
    description = fields.String(dump_only=True, allow_none=True)
    assignee_id = fields.UUID(dump_only=True, allow_none=True)
    assignee = fields.Nested(PublicUserSchema, dump_only=True, allow_none=True)
    due_date = fields.Date(dump_only=True, allow_none=True)
    order = fields.Float(dump_only=True)
    completed_at = UTCDateTime(dump_only=True, allow_none=True)
    created_by = fields.UUID(dump_only=True, allow_none=True)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)


class AssignedCardSchema(Schema):
    id = fields.UUID(dump_only=True)
    title = fields.String(dump_only=True)
    column_id = fields.UUID(dump_only=True)
    column_name = fields.String(dump_only=True)
    board_id = fields.UUID(dump_only=True)
    board_name = fields.String(dump_only=True)
    completed_at = UTCDateTime(dump_only=True, allow_none=True)
