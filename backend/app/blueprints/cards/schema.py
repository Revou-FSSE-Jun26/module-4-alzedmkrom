from marshmallow import Schema, ValidationError, fields, validates_schema
from marshmallow.validate import Length, OneOf, Range

from app.common.schemas import CardOutSchema
from app.common.validation import (
    LenientSchema,
    OrderValue,
    StrictBoolean,
    StrictSchema,
    StrictUUID,
    Text,
)


class CardCreateSchema(StrictSchema):
    # 'order', 'column_id', 'created_by' and 'completed' are unknown (Req 9.7).
    title = Text(required=True, validate=Length(1, 255))
    description = Text(allow_none=True, validate=Length(max=10000))
    assignee_id = StrictUUID(allow_none=True)


class CardUpdateSchema(StrictSchema):
    title = Text(validate=Length(1, 255))
    description = Text(allow_none=True, validate=Length(max=10000))
    assignee_id = StrictUUID(allow_none=True)
    completed = StrictBoolean()

    @validates_schema
    def at_least_one(self, data, **kwargs):
        # {} gives 400 (Req 9.10). Unknown fields are rejected by StrictSchema.
        if not data:
            raise ValidationError(
                "Provide title, description, assignee_id or completed", "_schema"
            )


class CardPositionSchema(LenientSchema):
    # Validated before the target column is looked up (Req 10.1, 10.5).
    column_id = StrictUUID(required=True)
    order = OrderValue(required=True, validate=Range(min=0, min_inclusive=False))


class SiblingOutSchema(Schema):
    id = fields.UUID(required=True)
    order = fields.Float(required=True)


class CardMoveOutSchema(CardOutSchema):
    column_id = fields.UUID(required=True)
    rebalanced = fields.Boolean(required=True)
    # Present only when rebalanced is true (Req 10.4).
    siblings = fields.List(fields.Nested(SiblingOutSchema))


class CardListQuerySchema(LenientSchema):
    # Unknown query keys are ignored.
    assignee = fields.String(validate=OneOf(["me"]))
    search = Text(validate=Length(1, 200))

    @validates_schema
    def exactly_one(self, data, **kwargs):
        if ("assignee" in data) == ("search" in data):
            message = "Provide exactly one of assignee or search"
            raise ValidationError(
                {"assignee": [message], "search": [message]}
            )


class TaskGroupOutSchema(Schema):
    board_id = fields.UUID(required=True)
    board_name = fields.String(required=True)
    cards = fields.List(fields.Nested(CardOutSchema), required=True)
