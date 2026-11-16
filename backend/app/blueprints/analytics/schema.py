from marshmallow import Schema, fields


class ColumnCountOutSchema(Schema):
    column_id = fields.UUID(required=True)
    title = fields.String(required=True)
    card_count = fields.Integer(required=True)


class MemberActivityOutSchema(Schema):
    user_id = fields.UUID(required=True)
    name = fields.String(required=True)
    actions = fields.Integer(required=True)


class AnalyticsOutSchema(Schema):
    cards_per_column = fields.List(fields.Nested(ColumnCountOutSchema), required=True)
    completed_this_week = fields.Integer(required=True)
    member_activity = fields.List(fields.Nested(MemberActivityOutSchema), required=True)
