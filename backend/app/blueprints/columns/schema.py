from marshmallow import Schema, fields
from marshmallow.validate import Length, Range

from app.common.schemas import ColumnOutSchema
from app.common.validation import LenientSchema, OrderValue, StrictUUID, Text


class ColumnCreateSchema(LenientSchema):
    title = Text(required=True, validate=Length(1, 255))


class ColumnUpdateSchema(ColumnCreateSchema):
    pass


class ColumnReorderSchema(LenientSchema):
    column_id = StrictUUID(required=True)
    order = OrderValue(required=True, validate=Range(min=0, min_inclusive=False))


class ColumnReorderOutSchema(Schema):
    columns = fields.List(fields.Nested(ColumnOutSchema), required=True)
    rebalanced = fields.Boolean(required=True)
