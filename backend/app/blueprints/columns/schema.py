from marshmallow import Schema, fields, validate

from app.schemas import NAME_MAX, PatchSchema, StrictSchema, Text, UTCDateTime


class ColumnCreateSchema(StrictSchema):
    name = Text(required=True, validate=validate.Length(min=1, max=NAME_MAX))


class ColumnUpdateSchema(PatchSchema):
    name = Text(validate=validate.Length(min=1, max=NAME_MAX))
    is_done = fields.Boolean()


class ColumnReorderSchema(StrictSchema):
    column_id = fields.UUID(required=True)
    order = fields.Float(required=True, validate=validate.Range(min=0, min_inclusive=False))


class ColumnSchema(Schema):
    id = fields.UUID(dump_only=True)
    board_id = fields.UUID(dump_only=True)
    name = fields.String(dump_only=True)
    order = fields.Float(dump_only=True)
    is_done = fields.Boolean(dump_only=True)
    created_by = fields.UUID(dump_only=True, allow_none=True)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)
