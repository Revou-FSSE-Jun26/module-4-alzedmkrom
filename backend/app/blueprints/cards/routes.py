from flask import Blueprint, jsonify, request

from app.auth_utils import auth_required, current_user
from app.blueprints.cards import service
from app.blueprints.cards.schema import (
    AssignedCardSchema,
    AssignedCardsQuerySchema,
    CardCreateSchema,
    CardPositionSchema,
    CardSchema,
    CardUpdateSchema,
)
from app.openapi import document

bp = Blueprint("cards", __name__)


@bp.post("/api/columns/<uuid:column_id>/cards")
@auth_required
@document(
    summary="Add a card to a column",
    tags=["cards"],
    request=CardCreateSchema,
    success=CardSchema,
    status=201,
)
def create_card(column_id):
    card = service.create_card(current_user(), column_id, request.get_json(silent=True))
    return jsonify(CardSchema().dump(card)), 201


@bp.get("/api/cards")
@auth_required
@document(
    summary="List cards assigned to me",
    tags=["cards"],
    success=AssignedCardSchema,
    many=True,
    query=AssignedCardsQuerySchema,
)
def list_assigned_cards():
    items, page, per_page, total, pages = service.list_assigned(
        current_user(), request.args.to_dict()
    )
    body = [
        AssignedCardSchema().dump(
            {
                "id": card.id,
                "title": card.title,
                "column_id": card.column_id,
                "column_name": column_name,
                "board_id": card.board_id,
                "board_name": board_name,
                "completed_at": card.completed_at,
            }
        )
        for card, column_name, board_name in items
    ]
    return jsonify(
        {
            "items": body,
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
        }
    ), 200


@bp.patch("/api/cards/<uuid:card_id>")
@auth_required
@document(
    summary="Edit a card",
    tags=["cards"],
    request=CardUpdateSchema,
    success=CardSchema,
)
def update_card(card_id):
    card = service.update_card(current_user(), card_id, request.get_json(silent=True))
    return jsonify(CardSchema().dump(card)), 200


@bp.patch("/api/cards/<uuid:card_id>/position")
@auth_required
@document(
    summary="Move a card to a column and position",
    tags=["cards"],
    request=CardPositionSchema,
    success=CardSchema,
)
def move_card(card_id):
    card, placement = service.move_card(current_user(), card_id, request.get_json(silent=True))
    body = {
        **CardSchema().dump(card),
        "rebalanced": placement.rebalanced,
        "siblings": placement.siblings(),
    }
    return jsonify(body), 200


@bp.delete("/api/cards/<uuid:card_id>")
@auth_required
@document(
    summary="Soft-delete a card",
    tags=["cards"],
    success=None,
    status=204,
)
def delete_card(card_id):
    service.delete_card(current_user(), card_id)
    return "", 204
