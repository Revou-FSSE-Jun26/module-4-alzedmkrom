from flask import Blueprint

from app.common.access import (
    get_card_for_user,
    get_column_for_user,
    require_card_deleter,
)
from app.common.auth import current_user, protected
from app.common.envelope import ok
from app.common.openapi import document
from app.common.schemas import CardOutSchema, IdOutSchema
from app.common.validation import load_body, load_query

from . import service
from .schema import (
    CardCreateSchema,
    CardListQuerySchema,
    CardMoveOutSchema,
    CardPositionSchema,
    CardUpdateSchema,
    TaskGroupOutSchema,
)

bp = Blueprint("cards", __name__)


@bp.post("/api/columns/<column_id>/cards")
@document(
    summary="Create a card in a column",
    request=CardCreateSchema,
    success=CardOutSchema,
    status=201,
    conflict=True,
)
@protected
def create_card(column_id):
    user = current_user()
    access = get_column_for_user(user.id, column_id)
    data = load_body(CardCreateSchema())
    card = service.create_card(user, access, data)
    return ok(CardOutSchema().dump(card), 201)


@bp.get("/api/cards")
@document(
    summary="List my tasks (assignee=me) or search cards (search=term)",
    query=CardListQuerySchema,
    # Two response shapes share this operation: TaskGroupOutSchema[] for
    # assignee=me and CardOutSchema[] for search. build_openapi (task 14.1)
    # documents `data` as a oneOf of the two.
    success=TaskGroupOutSchema,
    many=True,
    status=200,
)
@protected
def list_cards():
    user = current_user()
    params = load_query(CardListQuerySchema())
    if "assignee" in params:
        groups = service.list_my_tasks(user)
        return ok(TaskGroupOutSchema(many=True).dump(groups))
    cards = service.search(user, params["search"])
    return ok(CardOutSchema(many=True).dump(cards))


@bp.patch("/api/cards/<card_id>")
@document(
    summary="Update a card",
    request=CardUpdateSchema,
    success=CardOutSchema,
    status=200,
    conflict=True,
)
@protected
def update_card(card_id):
    user = current_user()
    access = get_card_for_user(user.id, card_id)
    data = load_body(CardUpdateSchema())
    card = service.update_card(user, access, data)
    return ok(CardOutSchema().dump(card))


@bp.delete("/api/cards/<card_id>")
@document(
    summary="Delete a card (admin or creator only)",
    success=IdOutSchema,
    status=200,
    conflict=True,
)
@protected
def delete_card(card_id):
    user = current_user()
    access = get_card_for_user(user.id, card_id)
    require_card_deleter(access, user.id)
    result = service.delete_card(user, access)
    return ok(IdOutSchema().dump(result))


@bp.patch("/api/cards/<card_id>/position")
@document(
    summary="Move a card to a column and order position",
    request=CardPositionSchema,
    success=CardMoveOutSchema,
    status=200,
    conflict=True,
)
@protected
def move_card(card_id):
    user = current_user()
    access = get_card_for_user(user.id, card_id)
    # Body is validated before the target column is looked up in the service.
    data = load_body(CardPositionSchema())
    result = service.move_card(user, access, data)
    return ok(CardMoveOutSchema().dump(result))
